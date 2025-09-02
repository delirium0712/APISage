# Contributing to APISage

Thank you for your interest in contributing to APISage! This document provides guidelines for contributing to our open source project.

## 📄 License Agreement

By contributing to APISage, you agree that your contributions will be licensed under the same **APISage Non-Commercial License** as the project.

### Key Points:
- ✅ **Open Source Contributions**: Welcome and encouraged
- ✅ **Non-Commercial Use**: All contributions must follow non-commercial terms
- ✅ **Organizational Use**: Contributions can be used internally by organizations
- ❌ **Commercial Use**: No commercial use of contributions allowed

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Poetry (for dependency management)
- Git

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd APISage

# Install dependencies
make install

# Set up environment
make setup-env
# Edit .env with your OpenAI API key

# Start development environment
make dev
```

## 📝 How to Contribute

### 1. **Bug Reports**
- Use GitHub Issues to report bugs
- Include steps to reproduce
- Provide system information (OS, Python version)
- Include relevant logs or error messages

### 2. **Feature Requests**
- Use GitHub Issues for feature requests
- Describe the use case and expected behavior
- Consider if the feature aligns with non-commercial use

### 3. **Code Contributions**

#### Pull Request Process:
1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes
4. **Test** your changes: `make test`
5. **Format** code: `make format`
6. **Lint** code: `make lint`
7. **Commit** changes: `git commit -m 'Add amazing feature'`
8. **Push** to branch: `git push origin feature/amazing-feature`
9. **Open** a Pull Request

#### Code Standards:
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings for functions and classes
- Write tests for new functionality
- Ensure all tests pass: `make test`

### 4. **Documentation**
- Update README.md for significant changes
- Add docstrings to new functions/classes
- Update API documentation if endpoints change
- Include examples for new features

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test file
poetry run pytest tests/test_specific.py

# Run with coverage
poetry run pytest --cov=api --cov=infrastructure
```

## 🔧 Development Tools

```bash
# Format code
make format

# Lint code
make lint

# Clean temporary files
make clean

# Check application status
make status
```

## 📋 Pull Request Guidelines

### Before Submitting:
- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Code is properly formatted (`make format`)
- [ ] No linting errors (`make lint`)
- [ ] Documentation updated if needed
- [ ] Commit messages are clear and descriptive

### PR Description Template:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## License Compliance
- [ ] Changes comply with Non-Commercial License
- [ ] No commercial use implications
```

## 🚫 What Not to Contribute

### Prohibited Contributions:
- Code that enables commercial monetization
- Features specifically designed for commercial use
- Integrations with commercial-only services
- Code that violates the non-commercial license

### Examples of Acceptable Contributions:
- Bug fixes and improvements
- New analysis features
- UI/UX enhancements
- Performance optimizations
- Documentation improvements
- Educational examples and tutorials

## 🤝 Community Guidelines

### Be Respectful:
- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Be Collaborative:
- Help others learn and grow
- Share knowledge and best practices
- Work together to solve problems
- Give credit where credit is due

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and community chat
- **Email**: teamalacrityai@gmail.com for commercial licensing inquiries

## 🎉 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- GitHub contributor statistics

Thank you for contributing to APISage! 🚀
