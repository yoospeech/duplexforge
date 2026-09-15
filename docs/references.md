# 설계에 참고한 공개 프로젝트

DuplexForge는 아래 프로젝트의 아이디어와 공개 문서를 참고했지만 코드를 복사하지 않고 독립적으로 구현했다.

- [DuplexGen](https://github.com/duplexgen/duplexgen-code): 구어체 변환, 발화 내부 슬롯, turn-taking 행동 생성, 2채널 TTS라는 단계 분리를 참고했다. 원 프로젝트 코드는 Apache-2.0이며 데이터는 원천 데이터셋별 라이선스가 다르다.
- [Full-Duplex Dialogue Data Preparation](https://github.com/HaoZhang6720/fullduplex-dialogue-data): real/fake interruption과 continue-listen 상태 구분을 참고했다. 해당 저장소는 PolyForm Noncommercial이므로 코드는 가져오지 않았다.
- [NVIDIA NeMo Speech Data Simulator](https://github.com/NVIDIA-NeMo/Speech/tree/main/tools/speech_data_simulator): silence/overlap을 절대 시간축 라벨로 표현하는 방식과 화자별 트랙 생성을 참고했다.
- [Full-Duplex-Bench](https://github.com/DanielLin94144/Full-Duplex-Bench): pause, backchannel, interruption, overlap이라는 평가 축을 데이터 패턴에 반영했다.
- [Easy-Turn](https://github.com/ASLP-lab/Easy-Turn): complete, incomplete, backchannel, wait 상태는 향후 품질 판별기 인터페이스를 설계할 때 활용할 수 있다.
- [MaAI](https://github.com/MaAI-Kyoto/MaAI): VAP 기반 turn-taking/backchannel timing 모델은 향후 합성 타이밍 감사기에 연결할 후보이다.
- [TensorRT-LLM trtllm-serve](https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve.html): Qwen3-8B-FP8을 OpenAI-compatible Chat Completions API로 서빙하는 기본 런타임이다.

`edge-tts` 백엔드는 편리한 프로토타이핑용이다. 서비스 약관, 생성 음성의 이용 조건 및 네트워크 의존성을 사용자가 별도로 확인해야 한다. 대규모 학습 데이터를 만들 때는 라이선스가 명확한 로컬 TTS 백엔드를 추가하는 것을 권장한다.
# Inference runtimes

- [NVIDIA TensorRT Edge-LLM supported models](https://github.com/NVIDIA/TensorRT-Edge-LLM/blob/main/docs/source/user_guide/getting_started/supported-models.md): Qwen3-TTS 0.6B/1.7B CustomVoice, VoiceDesign, Base 지원.
- [TensorRT Edge-LLM direct engine builder](https://github.com/NVIDIA/TensorRT-Edge-LLM/blob/main/docs/source/user_guide/getting_started/direct-engine-builder.md): TTS engine component와 `qwen3_tts_inference` 실행 방식.
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS): 모델 기능, 언어, 라이선스와 기준 구현.
