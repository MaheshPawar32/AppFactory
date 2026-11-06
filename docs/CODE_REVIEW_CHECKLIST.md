# AI-assisted code review checklist

Before accepting a Claude-generated change, review:

- [ ] Does it preserve existing routes, state management and business rules?
- [ ] Are all new UI actions wired to real behavior?
- [ ] Are loading/error/empty/offline states handled where relevant?
- [ ] Are controllers, subscriptions and animation resources disposed?
- [ ] Is async work safe when a widget is disposed or requests return out of order?
- [ ] Are validation and duplicate submissions handled?
- [ ] Are credentials, personal data and sensitive values kept out of logs/source?
- [ ] Are new dependencies necessary and compatible?
- [ ] Are tests added for changed behavior?
- [ ] Does the change match Nova UI and the supplied references?
- [ ] Are docs/changelog updated where behavior or public APIs changed?
- [ ] Are actual verification results recorded accurately?
