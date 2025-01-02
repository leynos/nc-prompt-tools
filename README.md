# 🎨 NovelCrafter Prompt Tools

Welcome to the NovelCrafter Prompt Tools collection! This jolly set of utilities is designed to make your NovelCrafter experience even more delightful.

Note: We are not affiliated in any way with the NovelCrafter developers, platform or service

## 🔍 Prompt Lint

Our star tool is the Prompt Lint - your friendly neighborhood prompt checker! It helps ensure your prompts are in tip-top shape before you share them on the NovelCrafter Discord.

### Installation

```bash
uv sync
```

### Usage

It's as easy as pie! Just run:

```bash
uv run prompt_lint your_prompt_file.json
```

To apply fixes, run:

```bash
uv run prompt_lint --fix your_prompt_file.json
```

### Features

- ✨ Validates prompt syntax
- 💡 Attempts naive fixes of missing parenthesis
- 🚀 Works right from your command line

## Contributing

Found a bug? Have a brilliant idea? We'd love to hear from you! Feel free to:
1. Open an issue
2. Submit a pull request
3. Share your thoughts

## License

This project is open source and available under the ISC license.

---
Made with ❤️ for the NovelCrafter community