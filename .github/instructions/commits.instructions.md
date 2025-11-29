---
applyTo: '**'
---

# Conventional Commits Instructions

Always follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification when creating commit messages.

## Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Types

Use one of the following types:

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc) |
| `refactor` | A code change that neither fixes a bug nor adds a feature |
| `perf` | A code change that improves performance |
| `test` | Adding missing tests or correcting existing tests |
| `build` | Changes that affect the build system or external dependencies |
| `ci` | Changes to CI configuration files and scripts |
| `chore` | Other changes that don't modify src or test files |
| `revert` | Reverts a previous commit |

## Rules

1. **Type is required** - Every commit must have a type prefix
2. **Description is required** - A short summary of the code changes (imperative mood, lowercase, no period at end)
3. **Scope is optional** - A noun describing a section of the codebase (e.g., `api`, `device`, `auth`)
4. **Body is optional** - Provide additional contextual information about the code changes
5. **Footer is optional** - Used for breaking changes and issue references
6. **Breaking changes** - Must be indicated by `!` after type/scope OR by `BREAKING CHANGE:` in footer
7. **Keep the subject line under 50 characters** when possible
8. **Wrap the body at 72 characters**

## Examples

### Simple feature
```
feat: add water heater temperature control
```

### Feature with scope
```
feat(api): add authentication token refresh
```

### Bug fix with body
```
fix(device): correct temperature unit conversion

The API returns Fahrenheit but was being treated as Celsius.
Added proper conversion logic in the device module.
```

### Breaking change with footer
```
feat(api)!: change authentication flow to OAuth2

BREAKING CHANGE: The API now requires OAuth2 tokens instead of API keys.
Users must update their authentication configuration.

Closes #123
```

### Documentation
```
docs: update README with installation instructions
```

### Multiple footers
```
fix(auth): resolve token expiration issue

The refresh token was not being properly stored after renewal.

Fixes #456
Reviewed-by: John Doe
```

## Scope Suggestions for This Project

- `api` - Changes to `aiorinnai/api.py`
- `device` - Changes to `aiorinnai/device.py`
- `user` - Changes to `aiorinnai/user.py`
- `types` - Changes to type definitions
- `errors` - Changes to error handling
- `deps` - Dependency updates
- `ci` - CI/CD configuration changes
