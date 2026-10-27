# 소스 검증 결과 (2026-10-27 23:42 UTC)

`python -m scripts.verify_sources --write`로 생성됨. 조사 근거는 docs/sources.md 참고.

| 소스 | URL | robots.txt | HTTP | 내용 |
|---|---|---|---|---|
| Anthropic News | https://www.anthropic.com/news | 허용 | 200 | 기사 18개, 예: Investing in the public benefit |
| OpenAI News | https://openai.com/news/rss.xml | 허용 | 200 | RSS 1331개, 최신: Tue, 27 Oct 2026 15:00:00 GMT |
| Google DeepMind Blog | https://deepmind.google/blog/rss.xml | 허용 | 200 | RSS 100개, 최신: Tue, 27 Oct 2026 16:01:38 +0000 |
| Meta AI Blog | https://ai.meta.com/blog/ | 허용 | 200 | 기사 5개, 예: Introducing Muse Spark 1.1 |
| NVIDIA Blog | https://blogs.nvidia.com/feed/ | 허용 | 200 | RSS 18개, 최신: Tue, 27 Oct 2026 15:00:20 +0000 |
| Hugging Face Daily Papers | https://huggingface.co/api/daily_papers | 허용 | 200 | JSON list (50개) |
| Epoch AI | https://epoch.ai/atom.xml | 허용 | 200 | RSS 50개, 최신: 2026-10-27T00:00:00.000Z |
| Stanford HAI News | https://hai.stanford.edu/news | 허용 | 200 | 기사 11개, 예: How AI Is Accelerating Scientific Discov |
| 소프트웨어정책연구소(SPRi) | https://spri.kr/posts?code=data_all | 허용 | 200 | 기사 12개, 예: 글로벌 AI 벤처투자 동향과 투자 집중구조: 국내 현황과 시사점 |
| 과학기술정보통신부 보도자료 | https://www.msit.go.kr/user/rss/rss.do?bbsSeqNo=94 | 허용 | 200 | RSS 50개, 최신: 2026.10.26 |
| 삼성 | https://www.samsungcareers.com | 허용 | 200 | HTML 56KB |
| SK | https://www.skcareers.com | 허용 | 200 | HTML 33KB |
| 현대자동차 | https://talent.hyundai.com | 허용 | 200 → https://talent.hyundai.com/main/netFunnel.hc | HTML 3KB — 내용이 적음, JS 렌더링 필요 가능성 |
| LG | https://careers.lg.com | 허용 | 200 | HTML 2KB — 내용이 적음, JS 렌더링 필요 가능성 |
| 한화 | https://www.hanwhain.com | 허용 | 200 | HTML 3KB — 내용이 적음, JS 렌더링 필요 가능성 |
| 롯데 | https://recruit.lotte.co.kr | robots.txt 403 | 200 | HTML 182KB |
| 포스코 | https://recruit.posco.com | 확인 실패 (ConnectError) | 실패 (ConnectError) | - |
| HD현대 | https://recruit.hd.com | 허용 | 200 | HTML 2KB — 내용이 적음, JS 렌더링 필요 가능성 |
| KT | https://recruit.kt.com/careers | 허용 | 200 | HTML 2KB — 내용이 적음, JS 렌더링 필요 가능성 |
| 고용24 공채속보 | https://www.data.go.kr/data/15031951/openapi.do | 허용 | 200 | JSON 아님 |
