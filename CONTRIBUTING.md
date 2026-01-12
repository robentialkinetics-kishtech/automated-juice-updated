# Contributing to ZKBot Controller

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Code of Conduct

Be respectful and professional. We aim to maintain a welcoming community.

## How to Contribute

### 1. Report Bugs

Create an issue with:
- **Title**: Clear, descriptive title
- **Environment**: OS, Python version, robot model
- **Steps to Reproduce**: Exact steps that cause the bug
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Logs**: Terminal output, error messages

### 2. Suggest Enhancements

Create an issue with:
- **Title**: Feature name
- **Description**: Why this feature is needed
- **Implementation Ideas**: How you'd approach it
- **Examples**: Use cases or examples

### 3. Code Contributions

#### Setup Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/automated-juice-updated.git
cd automated-juice-updated

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development tools (optional)
pip install pylint black pytest
```

#### Code Style

- **Python**: Follow PEP 8
- **Line Length**: Max 100 characters
- **Indentation**: 4 spaces
- **Naming**: 
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`

#### Making Changes

1. **Create a Feature Branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

2. **Make Your Changes**
   - Keep commits small and focused
   - Write clear commit messages
   - Test your changes

3. **Commit Messages**

Format: `Type: Description`

Types:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code restructuring
- `test:` Tests
- `style:` Formatting

Example:
```bash
git commit -m "feat: Add position history tracking"
git commit -m "fix: Resolve serial port timeout issue"
git commit -m "docs: Update README with examples"
```

4. **Push to Your Fork**
```bash
git push origin feature/your-feature-name
```

5. **Create Pull Request**
   - Go to GitHub
   - Click "Compare & pull request"
   - Fill in PR template:
     - What: What does this change?
     - Why: Why is this needed?
     - How: How does it work?
     - Testing: How was it tested?

## Development Guidelines

### Before Writing Code

- Check if similar functionality exists
- Discuss significant changes in an issue first
- Review existing code style and patterns

### Writing Code

- Add type hints where possible
- Write docstrings for classes and functions
- Keep functions small and focused (< 50 lines ideal)
- Use meaningful variable names
- Avoid global state

### Testing

Test your changes:

```bash
# Run diagnostics
python diagnose_serial.py

# Start GUI and manual test
python gui.py

# Test specific functionality
python test.py
```

### Documentation

Update documentation for:
- New features
- API changes
- Configuration options
- Installation steps

## Project Structure

```
zkbot_controller/
├── gui.py                 # Main application (keep clean & modular)
├── serial_comm.py         # Hardware layer (core functionality)
├── jog_control.py         # User interaction (UI-focused)
├── config.py              # Settings (no hardcoded values)
├── models.py              # Data structures (immutable where possible)
└── [other modules]        # Feature-specific code
```

## Areas for Contribution

### High Priority
- [ ] Web interface (Flask/React)
- [ ] Network communication (TCP/IP)
- [ ] Collision detection
- [ ] Motion optimization (ML)

### Medium Priority
- [ ] Better error handling
- [ ] Logging system
- [ ] Configuration validation
- [ ] Unit tests

### Low Priority
- [ ] UI improvements
- [ ] Performance optimization
- [ ] Code cleanup
- [ ] Documentation improvements

## Review Process

1. **Automated Checks**
   - Code formatting
   - Syntax errors
   - Import validation

2. **Manual Review**
   - Code quality
   - Design patterns
   - Safety implications
   - Documentation

3. **Testing**
   - Feature functionality
   - No regressions
   - Edge cases

4. **Approval**
   - At least 1 maintainer approval
   - All CI checks pass
   - Ready to merge

## Merge Conflicts

If your PR has conflicts:

```bash
# Update your branch
git fetch origin
git rebase origin/main

# Resolve conflicts in your editor
# Then continue rebase
git add .
git rebase --continue

# Force push to your fork
git push origin feature/your-feature --force
```

## After Merge

- Your branch will be deleted
- The feature will be in the next release
- You'll be credited as a contributor

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open a discussion on GitHub
- Review existing issues and PRs
- Check the README and SETUP.md

## Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes
- Project README

Thank you for contributing! 🎉
