# InkosAI Release Checklist

Pre-release checklist for InkosAI v0.1.0

## Status

**Current Version:** 0.1.0  
**Release Date:** 2025-04-27  
**Status:** Ready for Release

## Pre-Release Validation

### Code Quality

- [x] All tests passing (2100+)
- [x] Linting clean (ruff)
- [x] Type checking pass (mypy)
- [x] Security scan complete
- [x] No TODO/FIXME comments in production code
- [x] CHANGELOG.md updated

### Documentation

- [x] README.md has quick start
- [x] docs/DEPLOYMENT.md complete
- [x] docs/API.md complete  
- [x] docs/USER_GUIDE.md complete
- [x] CHANGELOG.md complete
- [x] CODE_OF_CONDUCT.md present
- [x] LICENSE file present

### CI/CD

- [x] GitHub Actions workflow passing
- [x] Docker image builds successfully
- [x] Security scans passing (Trivy, Bandit)
- [x] Integration tests passing

## Release Steps

### 1. Version Verification

```bash
# Check versions
pyproject.toml: 0.1.0
package.json (web): 0.1.0
apps/web/package.json: 0.1.0
services/api/version.py: 0.1.0

# Verify no development dependencies in production
# Verify DEBUG=false is default in docker-compose.yml
```

### 2. Final Test Run

```bash
# Full test suite
uv run pytest -xvs --tb=short

# With production-like settings
export ENVIRONMENT=production
export DEBUG=false
uv run pytest tests/ --tb=short

# Run smoke tests
docker-compose up -d
sleep 30
./scripts/smoke_tests.sh
```

### 3. Build Verification

```bash
# Build all images
docker-compose build

# Verify sizes
docker images | grep inkosai

# Export to check
docker save inkosai/api:latest | gzip > inkosai-api-v0.1.0.tar.gz
```

### 4. Tag Release

```bash
# Create tag
git tag -a v0.1.0 -m "Release v0.1.0 - Production Ready"

# Push tags
git push origin v0.1.0
```

### 5. Create GitHub Release

1. Go to GitHub → Releases
2. Click "Draft new release"
3. Choose tag: v0.1.0
4. Title: "v0.1.0 - Production Ready"
5. Copy CHANGELOG.md entry for v0.1.0
6. Attach assets:
   - Docker image tarball
   - Documentation PDF (optional)
7. Publish release

### 6. Post-Release

- [x] Announce on social media
- [x] Update website (if applicable)
- [x] Close milestone in GitHub Projects
- [x] Archive old branches

## Deployment Verification

### Production Environment

```bash
# Health check
curl https://api.inkos.ai/api/health

# Readiness check
curl https://api.inkos.ai/api/ready

# Metrics endpoint
curl https://api.inkos.ai/api/metrics

# Login test
curl -X POST https://api.inkos.ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "..."}'
```

### Monitoring

- [x] Prometheus scraping
- [x] Grafana dashboards loading
- [x] Jaeger traces receiving
- [x] Logs shipping to storage
- [x] Alerts configured

### Security

- [x] SSL certificates valid
- [x] Security headers active
- [x] Rate limiting enabled
- [x] Plugin sandbox mode set to docker

## Rollback Plan

If issues detected:

1. **Immediate**: Stop traffic to affected instances
2. **Identify**: Check logs/Tape for root cause
3. **Rollback**: Revert to previous tag
   ```bash
   git checkout v0.0.9  # previous stable
   docker-compose down && docker-compose up -d
   ```
4. **Fix**: Apply hotfix in patch release
5. **Communicate**: Post mortem and timeline

## Notes

- First stable release after extensive development
- Production readiness verified through CI/CD
- Documentation complete for all major features
- Monitoring and observability fully operational

## Sign-Off

- [ ] **QA Lead**: Tested and ready
- [ ] **Security Lead**: Security scan passed
- [ ] **Infrastructure Lead**: Deployment tested
- [ ] **Product Lead**: Feature set approved
- [ ] **Release Manager**: Final approval

---

Released: v0.1.0 by InkosAI Team
