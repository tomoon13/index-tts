"""
Speech Length Control Patch for IndexTTS2
==========================================

This patch implements PR #505: https://github.com/index-tts/index-tts/pull/505
It adds support for target audio duration control via the `speech_length` parameter.

Usage:
    Simply import this module AFTER importing IndexTTS2 to apply the patch:

    from indextts.infer_v2 import IndexTTS2
    import speech_length_patch  # Apply the patch

    # Now IndexTTS2 supports speech_length parameter
    tts = IndexTTS2(...)
    tts.infer(..., speech_length=5000)  # Generate 5-second audio

To disable:
    Comment out or remove the import line.

When upstream merges PR #505:
    Simply delete this file and remove the import.
"""

import warnings
import time
import os
import random
import torch
import torchaudio
from indextts.infer_v2 import IndexTTS2, find_most_similar_cosine


def patched_infer_generator(self, spk_audio_prompt, text, output_path,
          emo_audio_prompt=None, emo_alpha=1.0,
          emo_vector=None,
          use_emo_text=False, emo_text=None, use_random=False, interval_silence=200,
          verbose=False, max_text_tokens_per_segment=120, stream_return=False, quick_streaming_tokens=0, **generation_kwargs):
    print(">> starting inference...")
    self._set_gr_progress(0, "starting inference...")
    if verbose:
        print(f"origin text:{text}, spk_audio_prompt:{spk_audio_prompt}, "
              f"emo_audio_prompt:{emo_audio_prompt}, emo_alpha:{emo_alpha}, "
              f"emo_vector:{emo_vector}, use_emo_text:{use_emo_text}, "
              f"emo_text:{emo_text}")
    start_time = time.perf_counter()

    if use_emo_text or emo_vector is not None:
        # we're using a text or emotion vector guidance; so we must remove
        # "emotion reference voice", to ensure we use correct emotion mixing!
        emo_audio_prompt = None

    if use_emo_text:
        # automatically generate emotion vectors from text prompt
        if emo_text is None:
            emo_text = text  # use main text prompt
        emo_dict = self.qwen_emo.inference(emo_text)
        print(f"detected emotion vectors from text: {emo_dict}")
        # convert ordered dict to list of vectors; the order is VERY important!
        emo_vector = list(emo_dict.values())

    if emo_vector is not None:
        # we have emotion vectors; they can't be blended via alpha mixing
        # in the main inference process later, so we must pre-calculate
        # their new strengths here based on the alpha instead!
        emo_vector_scale = max(0.0, min(1.0, emo_alpha))
        if emo_vector_scale != 1.0:
            # scale each vector and truncate to 4 decimals (for nicer printing)
            emo_vector = [int(x * emo_vector_scale * 10000) / 10000 for x in emo_vector]
            print(f"scaled emotion vectors to {emo_vector_scale}x: {emo_vector}")

    if emo_audio_prompt is None:
        # we are not using any external "emotion reference voice"; use
        # speaker's voice as the main emotion reference audio.
        emo_audio_prompt = spk_audio_prompt
        # must always use alpha=1.0 when we don't have an external reference voice
        emo_alpha = 1.0

    # 如果参考音频改变了，才需要重新生成, 提升速度
    if self.cache_spk_cond is None or self.cache_spk_audio_prompt != spk_audio_prompt:
        if self.cache_spk_cond is not None:
            self.cache_spk_cond = None
            self.cache_s2mel_style = None
            self.cache_s2mel_prompt = None
            self.cache_mel = None
            torch.cuda.empty_cache()
        audio,sr = self._load_and_cut_audio(spk_audio_prompt,15,verbose)
        audio_22k = torchaudio.transforms.Resample(sr, 22050)(audio)
        audio_16k = torchaudio.transforms.Resample(sr, 16000)(audio)

        inputs = self.extract_features(audio_16k, sampling_rate=16000, return_tensors="pt")
        input_features = inputs["input_features"]
        attention_mask = inputs["attention_mask"]
        input_features = input_features.to(self.device)
        attention_mask = attention_mask.to(self.device)
        spk_cond_emb = self.get_emb(input_features, attention_mask)

        _, S_ref = self.semantic_codec.quantize(spk_cond_emb)
        ref_mel = self.mel_fn(audio_22k.to(spk_cond_emb.device).float())
        ref_target_lengths = torch.LongTensor([ref_mel.size(2)]).to(ref_mel.device)
        feat = torchaudio.compliance.kaldi.fbank(audio_16k.to(ref_mel.device),
                                                 num_mel_bins=80,
                                                 dither=0,
                                                 sample_frequency=16000)
        feat = feat - feat.mean(dim=0, keepdim=True)  # feat2另外一个滤波器能量组特征[922, 80]
        style = self.campplus_model(feat.unsqueeze(0))  # 参考音频的全局style2[1,192]

        prompt_condition = self.s2mel.models['length_regulator'](S_ref,
                                                                 ylens=ref_target_lengths,
                                                                 n_quantizers=3,
                                                                 f0=None)[0]

        self.cache_spk_cond = spk_cond_emb
        self.cache_s2mel_style = style
        self.cache_s2mel_prompt = prompt_condition
        self.cache_spk_audio_prompt = spk_audio_prompt
        self.cache_mel = ref_mel
    else:
        style = self.cache_s2mel_style
        prompt_condition = self.cache_s2mel_prompt
        spk_cond_emb = self.cache_spk_cond
        ref_mel = self.cache_mel

    if emo_vector is not None:
        weight_vector = torch.tensor(emo_vector, device=self.device)
        if use_random:
            random_index = [random.randint(0, x - 1) for x in self.emo_num]
        else:
            random_index = [find_most_similar_cosine(style, tmp) for tmp in self.spk_matrix]

        emo_matrix = [tmp[index].unsqueeze(0) for index, tmp in zip(random_index, self.emo_matrix)]
        emo_matrix = torch.cat(emo_matrix, 0)
        emovec_mat = weight_vector.unsqueeze(1) * emo_matrix
        emovec_mat = torch.sum(emovec_mat, 0)
        emovec_mat = emovec_mat.unsqueeze(0)

    if self.cache_emo_cond is None or self.cache_emo_audio_prompt != emo_audio_prompt:
        if self.cache_emo_cond is not None:
            self.cache_emo_cond = None
            torch.cuda.empty_cache()
        emo_audio, _ = self._load_and_cut_audio(emo_audio_prompt,15,verbose,sr=16000)
        emo_inputs = self.extract_features(emo_audio, sampling_rate=16000, return_tensors="pt")
        emo_input_features = emo_inputs["input_features"]
        emo_attention_mask = emo_inputs["attention_mask"]
        emo_input_features = emo_input_features.to(self.device)
        emo_attention_mask = emo_attention_mask.to(self.device)
        emo_cond_emb = self.get_emb(emo_input_features, emo_attention_mask)

        self.cache_emo_cond = emo_cond_emb
        self.cache_emo_audio_prompt = emo_audio_prompt
    else:
        emo_cond_emb = self.cache_emo_cond

    self._set_gr_progress(0.1, "text processing...")
    text_tokens_list = self.tokenizer.tokenize(text)
    segments = self.tokenizer.split_segments(text_tokens_list, max_text_tokens_per_segment, quick_streaming_tokens = quick_streaming_tokens)
    segments_count = len(segments)

    text_token_ids = self.tokenizer.convert_tokens_to_ids(text_tokens_list)
    if self.tokenizer.unk_token_id in text_token_ids:
        print(f"  >> Warning: input text contains {text_token_ids.count(self.tokenizer.unk_token_id)} unknown tokens (id={self.tokenizer.unk_token_id}):")
        print( "     Tokens which can't be encoded: ", [t for t, id in zip(text_tokens_list, text_token_ids) if id == self.tokenizer.unk_token_id])
        print(f"     Consider updating the BPE model or modifying the text to avoid unknown tokens.")

    if verbose:
        print("text_tokens_list:", text_tokens_list)
        print("segments count:", segments_count)
        print("max_text_tokens_per_segment:", max_text_tokens_per_segment)
        print(*segments, sep="\n")
    do_sample = generation_kwargs.pop("do_sample", True)
    top_p = generation_kwargs.pop("top_p", 0.8)
    top_k = generation_kwargs.pop("top_k", 30)
    temperature = generation_kwargs.pop("temperature", 0.8)
    autoregressive_batch_size = 1
    length_penalty = generation_kwargs.pop("length_penalty", 0.0)
    num_beams = generation_kwargs.pop("num_beams", 3)
    repetition_penalty = generation_kwargs.pop("repetition_penalty", 10.0)
    max_mel_tokens = generation_kwargs.pop("max_mel_tokens", 1500)
    # PATCH: Extract speech_length parameter (PR #505)
    speech_length = int(generation_kwargs.pop("speech_length", 0))
    sampling_rate = 22050

    wavs = []
    gpt_gen_time = 0
    gpt_forward_time = 0
    s2mel_time = 0
    bigvgan_time = 0
    has_warned = False
    silence = None # for stream_return
    for seg_idx, sent in enumerate(segments):
        self._set_gr_progress(0.2 + 0.7 * seg_idx / segments_count,
                              f"speech synthesis {seg_idx + 1}/{segments_count}...")

        text_tokens = self.tokenizer.convert_tokens_to_ids(sent)
        text_tokens = torch.tensor(text_tokens, dtype=torch.int32, device=self.device).unsqueeze(0)
        if verbose:
            print(text_tokens)
            print(f"text_tokens shape: {text_tokens.shape}, text_tokens type: {text_tokens.dtype}")
            # debug tokenizer
            text_token_syms = self.tokenizer.convert_ids_to_tokens(text_tokens[0].tolist())
            print("text_token_syms is same as segment tokens", text_token_syms == sent)

        m_start_time = time.perf_counter()
        with torch.no_grad():
            with torch.amp.autocast(text_tokens.device.type, enabled=self.dtype is not None, dtype=self.dtype):
                emovec = self.gpt.merge_emovec(
                    spk_cond_emb,
                    emo_cond_emb,
                    torch.tensor([spk_cond_emb.shape[-1]], device=text_tokens.device),
                    torch.tensor([emo_cond_emb.shape[-1]], device=text_tokens.device),
                    alpha=emo_alpha
                )

                if emo_vector is not None:
                    emovec = emovec_mat + (1 - torch.sum(weight_vector)) * emovec
                    # emovec = emovec_mat

                codes, speech_conditioning_latent = self.gpt.inference_speech(
                    spk_cond_emb,
                    text_tokens,
                    emo_cond_emb,
                    cond_lengths=torch.tensor([spk_cond_emb.shape[-1]], device=text_tokens.device),
                    emo_cond_lengths=torch.tensor([emo_cond_emb.shape[-1]], device=text_tokens.device),
                    emo_vec=emovec,
                    do_sample=True,
                    top_p=top_p,
                    top_k=top_k,
                    temperature=temperature,
                    num_return_sequences=autoregressive_batch_size,
                    length_penalty=length_penalty,
                    num_beams=num_beams,
                    repetition_penalty=repetition_penalty,
                    max_generate_length=max_mel_tokens,
                    **generation_kwargs
                )

            gpt_gen_time += time.perf_counter() - m_start_time
            if not has_warned and (codes[:, -1] != self.stop_mel_token).any():
                warnings.warn(
                    f"WARN: generation stopped due to exceeding `max_mel_tokens` ({max_mel_tokens}). "
                    f"Input text tokens: {text_tokens.shape[1]}. "
                    f"Consider reducing `max_text_tokens_per_segment`({max_text_tokens_per_segment}) or increasing `max_mel_tokens`.",
                    category=RuntimeWarning
                )
                has_warned = True

            code_lens = torch.tensor([codes.shape[-1]], device=codes.device, dtype=codes.dtype)
            #                 if verbose:
            #                     print(codes, type(codes))
            #                     print(f"codes shape: {codes.shape}, codes type: {codes.dtype}")
            #                     print(f"code len: {code_lens}")

            code_lens = []
            max_code_len = 0
            for code in codes:
                if self.stop_mel_token not in code:
                    code_len = len(code)
                else:
                    len_ = (code == self.stop_mel_token).nonzero(as_tuple=False)[0]
                    code_len = len_[0].item() if len_.numel() > 0 else len(code)
                code_lens.append(code_len)
                max_code_len = max(max_code_len, code_len)
            codes = codes[:, :max_code_len]
            code_lens = torch.LongTensor(code_lens)
            code_lens = code_lens.to(self.device)
            if verbose:
                print(codes, type(codes))
                print(f"fix codes shape: {codes.shape}, codes type: {codes.dtype}")
                print(f"code len: {code_lens}")

            m_start_time = time.perf_counter()
            use_speed = torch.zeros(spk_cond_emb.size(0)).to(spk_cond_emb.device).long()
            with torch.amp.autocast(text_tokens.device.type, enabled=self.dtype is not None, dtype=self.dtype):
                latent = self.gpt(
                    speech_conditioning_latent,
                    text_tokens,
                    torch.tensor([text_tokens.shape[-1]], device=text_tokens.device),
                    codes,
                    torch.tensor([codes.shape[-1]], device=text_tokens.device),
                    emo_cond_emb,
                    cond_mel_lengths=torch.tensor([spk_cond_emb.shape[-1]], device=text_tokens.device),
                    emo_cond_mel_lengths=torch.tensor([emo_cond_emb.shape[-1]], device=text_tokens.device),
                    emo_vec=emovec,
                    use_speed=use_speed,
                )
                gpt_forward_time += time.perf_counter() - m_start_time

            dtype = None
            with torch.amp.autocast(text_tokens.device.type, enabled=dtype is not None, dtype=dtype):
                m_start_time = time.perf_counter()
                diffusion_steps = 25
                inference_cfg_rate = 0.7
                latent = self.s2mel.models['gpt_layer'](latent)
                S_infer = self.semantic_codec.quantizer.vq2emb(codes.unsqueeze(1))
                S_infer = S_infer.transpose(1, 2)
                S_infer = S_infer + latent

                # PATCH: Speech length control logic (PR #505)
                base_target_lengths = (code_lens * 1.72).long()
                if speech_length == 0:
                    target_lengths = base_target_lengths
                else:
                    frame_duration = 11.61  # mel token duration ms = 256 / sampling rate * 1000
                    len_total = len(text_tokens_list)  # total token amount
                    len_current = len(sent)  # current token amount

                    if len_total <= 0:  # use default audio duration logic if something breaks
                        target_lengths = base_target_lengths
                        print(f"!!! Falling back to default duration logic for {seg_idx} segment")
                    else:
                        duration_ratio = len_current / len_total
                        target_chunk_ms = speech_length * duration_ratio
                        print(f">> Generating segment {seg_idx}: {duration_ratio*100:.2f}% of total audio duration ({int(target_chunk_ms)}ms)")
                        len_tensor = torch.LongTensor([int(speech_length*duration_ratio)])
                        len_tensor = len_tensor.to(self.device)
                        target_lengths = torch.clamp((len_tensor/frame_duration).long(), min=1)

                cond = self.s2mel.models['length_regulator'](S_infer,
                                                             ylens=target_lengths,
                                                             n_quantizers=3,
                                                             f0=None)[0]
                cat_condition = torch.cat([prompt_condition, cond], dim=1)
                vc_target = self.s2mel.models['cfm'].inference(cat_condition,
                                                               torch.LongTensor([cat_condition.size(1)]).to(
                                                                   cond.device),
                                                               ref_mel, style, None, diffusion_steps,
                                                               inference_cfg_rate=inference_cfg_rate)
                vc_target = vc_target[:, :, ref_mel.size(-1):]
                s2mel_time += time.perf_counter() - m_start_time

                m_start_time = time.perf_counter()
                wav = self.bigvgan(vc_target.float()).squeeze().unsqueeze(0)
                print(wav.shape)
                bigvgan_time += time.perf_counter() - m_start_time
                wav = wav.squeeze(1)

            wav = torch.clamp(32767 * wav, -32767.0, 32767.0)
            if verbose:
                print(f"wav shape: {wav.shape}", "min:", wav.min(), "max:", wav.max())
            # wavs.append(wav[:, :-512])
            wavs.append(wav.cpu())  # to cpu before saving
            if stream_return:
                yield wav.cpu()
                if silence == None:
                    silence = self.interval_silence(wavs, sampling_rate=sampling_rate, interval_silence=interval_silence)
                yield silence
    end_time = time.perf_counter()

    self._set_gr_progress(0.9, "saving audio...")
    wavs = self.insert_interval_silence(wavs, sampling_rate=sampling_rate, interval_silence=interval_silence)
    wav = torch.cat(wavs, dim=1)
    wav_length = wav.shape[-1] / sampling_rate
    print(f">> gpt_gen_time: {gpt_gen_time:.2f} seconds")
    print(f">> gpt_forward_time: {gpt_forward_time:.2f} seconds")
    print(f">> s2mel_time: {s2mel_time:.2f} seconds")
    print(f">> bigvgan_time: {bigvgan_time:.2f} seconds")
    print(f">> Total inference time: {end_time - start_time:.2f} seconds")
    print(f">> Generated audio length: {wav_length:.2f} seconds")
    print(f">> RTF: {(end_time - start_time) / wav_length:.4f}")

    # save audio
    wav = wav.cpu()  # to cpu
    if output_path:
        # 直接保存音频到指定路径中
        if os.path.isfile(output_path):
            os.remove(output_path)
            print(">> remove old wav file:", output_path)
        if os.path.dirname(output_path) != "":
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        torchaudio.save(output_path, wav.type(torch.int16), sampling_rate)
        print(">> wav file saved to:", output_path)
        if stream_return:
            return None
        yield output_path
    else:
        if stream_return:
            return None
        # 返回以符合Gradio的格式要求
        wav_data = wav.type(torch.int16)
        wav_data = wav_data.numpy().T
        yield (sampling_rate, wav_data)


# Apply the patch
print(">> Applying speech_length patch to IndexTTS2...")
IndexTTS2.infer_generator = patched_infer_generator
print(">> Patch applied successfully! IndexTTS2 now supports 'speech_length' parameter.")
