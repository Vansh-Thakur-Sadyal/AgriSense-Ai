# Changelog

All notable changes to AgriSense AI. Versions follow [Semantic Versioning](https://semver.org/):
`MAJOR.MINOR.PATCH`. MAJOR for changes that break the API or the database, MINOR for new features,
PATCH for bug fixes.

## [Unreleased]

### Documentation
- Rebuilt the GitHub README with numbered navigation, setup and deployment guides, feature limitations, architecture and workflow diagrams, screenshots, a branded logo, and an animated product tour.

## [1.0.0] - 2026-11-24

First version under git. Matches the build deployed at https://ai.software.microeagle.online (server release 9).

### Server and web dashboard
- FastAPI server with e-mail one-time-code sign-in (via n8n), farms, history, PDF/CSV reports.
- Crop recommendation (Random Forest, 99.55% test accuracy).
- Yield prediction (LightGBM, MAE 0.8744 t/ha, R2 0.9424 on unseen years).
- Fertiliser recommendation (Logistic Regression on N, P, K with the shortfall reasoning step).
- Leaf-disease detection (EfficientNet-B0 via ONNX, 99.77% test accuracy, calibrated, 0.95 threshold).
- AI assistant (Mistral) in 15 languages with the no-dose rule.
- Weather (Open-Meteo, NASA POWER), soil (ISRIC SoilGrids), interface translation (Azure).
- 88 automated tests; load test: 100 users at once with 95% of answers under 2 s.

### Android app (`android/`)
- Kotlin + Jetpack Compose client on the same API, bearer-token sessions, 3-second welcome screen.
