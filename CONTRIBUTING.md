# Contributing to OBS Docker Container

Thank you for your interest in contributing to the OBS Docker Container project! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

1. **Search existing issues** first to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information**:
   - Operating system and version
   - Docker version
   - Container logs (if applicable)
   - Steps to reproduce
   - Expected vs actual behavior

### Suggesting Features

1. **Check existing feature requests** to avoid duplicates
2. **Describe the use case** and why it would be valuable
3. **Consider implementation complexity** and maintenance burden
4. **Provide mockups or examples** if applicable

### Code Contributions

#### Prerequisites

- Docker installed and running
- Basic knowledge of Docker, Linux, and shell scripting
- Familiarity with OBS Studio (helpful but not required)

#### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd obs-docker

# Copy environment template
cp .env.example .env

# Build and test locally
make build
make run

# Run tests
chmod +x tests/test-container.sh
./tests/test-container.sh
```

#### Making Changes

1. **Fork the repository** and create a feature branch
2. **Follow coding standards** (see below)
3. **Test your changes** thoroughly
4. **Update documentation** as needed
5. **Submit a pull request**

## 📋 Coding Standards

### Shell Scripts

- Use `#!/bin/bash -e` or `#!/bin/bash -euo pipefail`
- Include proper error handling
- Add logging with timestamps
- Use meaningful variable names
- Comment complex logic
- Follow [ShellCheck](https://www.shellcheck.net/) recommendations

### Dockerfile

- Use multi-stage builds when appropriate
- Minimize layers and image size
- Pin versions for reproducibility
- Use build arguments for flexibility
- Include health checks
- Follow [Docker best practices](https://docs.docker.com/develop/dev-best-practices/)

### Documentation

- Use clear, concise language
- Include code examples
- Update README.md for user-facing changes
- Add inline comments for complex code
- Use proper Markdown formatting

## 🧪 Testing

### Required Tests

All contributions must include appropriate tests:

1. **Unit tests** for individual functions/scripts
2. **Integration tests** for container functionality
3. **Manual testing** on multiple architectures (if possible)

### Running Tests

```bash
# Run all tests
make test

# Run specific test
./tests/test-container.sh

# Run health check
docker exec obs-studio /scripts/health-check.sh
```

### Test Coverage

- Test both success and failure scenarios
- Verify error handling and logging
- Test on multiple architectures when possible
- Include performance/resource usage tests

## 🏗️ Architecture Support

This project supports multiple architectures:

- **AMD64** (x86_64) - Primary development platform
- **ARM64** (aarch64) - Apple Silicon, modern ARM servers
- **ARM/v7** - Raspberry Pi and similar devices

### Multi-Architecture Guidelines

- Test changes on multiple architectures
- Use architecture-agnostic installation methods
- Avoid hardcoded architecture-specific URLs
- Use build arguments for architecture-specific logic

## 📦 Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Release Checklist

- [ ] Update version numbers in relevant files
- [ ] Update CHANGELOG.md
- [ ] Test on all supported architectures
- [ ] Update documentation
- [ ] Create release notes
- [ ] Tag release in Git

## 🔒 Security

### Security Guidelines

- Never commit secrets or passwords
- Use strong default passwords with warnings
- Follow principle of least privilege
- Keep dependencies updated
- Report security issues privately

### Reporting Security Issues

Please report security vulnerabilities privately by:

1. **Email**: [security-email] (if available)
2. **GitHub Security**: Use GitHub's private vulnerability reporting
3. **Include**: Detailed description, reproduction steps, potential impact

## 📝 Pull Request Process

### Before Submitting

- [ ] Code follows project standards
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is up-to-date with main

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (specify)

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Multi-architecture testing (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### Review Process

1. **Automated checks** must pass
2. **Code review** by maintainers
3. **Testing** on multiple platforms
4. **Documentation review**
5. **Final approval** and merge

## 🎯 Development Priorities

### Current Focus Areas

1. **Performance optimization**
2. **Security improvements**
3. **Multi-architecture support**
4. **Documentation enhancement**
5. **Test coverage expansion**

### Future Roadmap

- GPU acceleration support
- Additional desktop environments
- Plugin ecosystem
- Cloud deployment guides
- Performance monitoring

## 💬 Communication

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check README and wiki first

### Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Share knowledge and experiences
- Follow the code of conduct

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

## 🙏 Recognition

Contributors will be recognized in:

- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to the OBS Docker Container project!
