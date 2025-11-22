# RecruitPro Troubleshooting Guide

**Quick solutions to common production issues**

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Database Issues](#database-issues)
3. [Redis/Queue Issues](#redisqueue-issues)
4. [Gemini API Issues](#gemini-api-issues)
5. [Worker Not Processing Jobs](#worker-not-processing-jobs)
6. [Application Won't Start](#application-wont-start)
7. [Performance Issues](#performance-issues)
8. [Connection Issues](#connection-issues)
9. [File Upload Issues](#file-upload-issues)
10. [Authentication Issues](#authentication-issues)

---

## Quick Diagnostics

### Check Overall System Health

```bash
curl http://localhost:8000/api/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy"},
    "queue": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "gemini_api": {"status": "healthy"}
  }
}
```

### Check Queue Status

```bash
curl http://localhost:8000/api/queue/status
```

### Check Service Status (Systemd)

```bash
sudo systemctl status recruitpro-web
sudo systemctl status recruitpro-worker
```

### View Recent Logs

```bash
# Web server logs
sudo journalctl -u recruitpro-web -n 100 --no-pager

# Worker logs
sudo journalctl -u recruitpro-worker -n 100 --no-pager

# Follow logs in real-time
sudo journalctl -u recruitpro-web -f
```

---

## Database Issues

### Issue: "Database connection failed"

**Symptoms:**
- Health check shows database as "unhealthy"
- Error: `could not connect to server`

**Solutions:**

1. **Check database is running:**
   ```bash
   # For local PostgreSQL
   sudo systemctl status postgresql

   # Test connection
   psql $RECRUITPRO_DATABASE_URL -c "SELECT 1"
   ```

2. **Verify connection string:**
   ```bash
   # Check .env file
   grep DATABASE_URL .env

   # Test format: postgresql://user:password@host:port/database
   ```

3. **Check firewall rules:**
   ```bash
   # For cloud databases, check security groups/firewall rules
   # Allow connections from your server's IP
   ```

4. **Check credentials:**
   ```bash
   # Test with psql
   psql "postgresql://user:password@host:5432/database"
   ```

### Issue: "Too many connections"

**Symptoms:**
- Error: `FATAL: sorry, too many clients already`

**Solutions:**

1. **Check active connections:**
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

2. **Close idle connections:**
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE datname = 'recruitpro'
   AND state = 'idle';
   ```

3. **Increase connection limit (if you have access):**
   ```sql
   ALTER SYSTEM SET max_connections = 100;
   SELECT pg_reload_conf();
   ```

### Issue: "Migrations failed"

**Symptoms:**
- Error: `alembic.util.exc.CommandError`

**Solutions:**

1. **Check migration status:**
   ```bash
   alembic current
   alembic history
   ```

2. **Reset to specific version:**
   ```bash
   # Downgrade to base
   alembic downgrade base

   # Upgrade to head
   alembic upgrade head
   ```

3. **Manual fix (last resort):**
   ```bash
   # Drop alembic_version table and recreate
   psql $RECRUITPRO_DATABASE_URL -c "DROP TABLE IF EXISTS alembic_version;"
   alembic stamp head
   ```

---

## Redis/Queue Issues

### Issue: "Redis connection failed"

**Symptoms:**
- Health check shows redis as "unhealthy"
- Error: `ConnectionRefusedError: [Errno 111] Connection refused`

**Solutions:**

1. **Check Redis is running:**
   ```bash
   # For local Redis
   redis-cli ping
   # Should return: PONG

   # Check service status
   sudo systemctl status redis
   ```

2. **Test Redis connection:**
   ```bash
   # Test with redis-cli
   redis-cli -u $REDIS_URL ping
   ```

3. **Check Redis URL format:**
   ```bash
   # Correct formats:
   # redis://localhost:6379/0
   # redis://:password@host:6379/0
   # redis://default:password@host:6379/0

   grep REDIS_URL .env
   ```

4. **Start Redis:**
   ```bash
   # macOS
   brew services start redis

   # Linux
   sudo systemctl start redis

   # Docker
   docker run -d -p 6379:6379 redis:7-alpine
   ```

### Issue: "Queue backend is in-memory instead of Redis"

**Symptoms:**
- Queue stats show `"backend": "in-memory (thread-based)"`

**Solutions:**

1. **Enable Redis queue:**
   ```bash
   # Add to .env
   USE_REDIS_QUEUE=true
   REDIS_URL=redis://localhost:6379/0
   ```

2. **Restart application:**
   ```bash
   sudo systemctl restart recruitpro-web recruitpro-worker
   ```

3. **Verify:**
   ```bash
   curl http://localhost:8000/api/queue/status
   # Should show: "backend": "redis + rq"
   ```

### Issue: "Jobs stuck in queue"

**Symptoms:**
- Jobs are queued but not processing
- Queue status shows queued jobs but no workers

**Solutions:**

1. **Check worker is running:**
   ```bash
   sudo systemctl status recruitpro-worker

   # If not running, start it
   sudo systemctl start recruitpro-worker
   ```

2. **Check worker logs:**
   ```bash
   sudo journalctl -u recruitpro-worker -n 50
   ```

3. **Manually process a job (testing):**
   ```bash
   # In Python console
   python3 -c "
   from app.services.queue import background_queue
   print(background_queue.stats())
   "
   ```

4. **Clear stuck jobs (if needed):**
   ```bash
   # Connect to Redis
   redis-cli -u $REDIS_URL

   # List queues
   KEYS rq:queue:*

   # Clear specific queue (CAREFUL!)
   DEL rq:queue:recruitpro
   ```

---

## Gemini API Issues

### Issue: "Gemini API key not configured"

**Symptoms:**
- Health check shows gemini_api as "degraded"
- AI features return errors

**Solutions:**

1. **Set API key:**
   ```bash
   # Add to .env
   GEMINI_API_KEY=AIza...your-key-here

   # Restart application
   sudo systemctl restart recruitpro-web recruitpro-worker
   ```

2. **Verify API key:**
   ```bash
   # Test API key
   curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=YOUR_API_KEY"
   ```

### Issue: "Gemini API quota exceeded"

**Symptoms:**
- Error: `429 Too Many Requests`
- Error: `Resource has been exhausted`

**Solutions:**

1. **Check quota usage:**
   - Go to [Google AI Studio](https://ai.google.dev)
   - Check your usage dashboard

2. **Wait for quota reset:**
   - Free tier: 15 requests/minute, 1500 requests/day
   - Resets at midnight UTC

3. **Upgrade to paid tier:**
   - Go to Google Cloud Console
   - Enable billing for higher limits

### Issue: "Gemini API timeout"

**Symptoms:**
- Error: `httpx.ReadTimeout`
- Jobs failing with timeout errors

**Solutions:**

1. **Check network connectivity:**
   ```bash
   curl https://generativelanguage.googleapis.com
   ```

2. **Increase timeout (if needed):**
   - Current timeout: 30 seconds
   - Modify in `app/services/gemini.py`:
   ```python
   httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))
   ```

3. **Check for large documents:**
   - CVs > 50 pages may time out
   - Split documents or process in chunks

---

## Worker Not Processing Jobs

### Issue: "Worker shows no activity"

**Symptoms:**
- Worker is running but not processing jobs
- Jobs accumulate in queue

**Solutions:**

1. **Check worker logs:**
   ```bash
   sudo journalctl -u recruitpro-worker -f
   ```

2. **Verify handlers are registered:**
   ```bash
   python3 -c "
   from app.services.queue import _HANDLER_REGISTRY
   print('Registered handlers:', list(_HANDLER_REGISTRY.keys()))
   "
   ```

3. **Restart worker:**
   ```bash
   sudo systemctl restart recruitpro-worker
   ```

4. **Check for errors in worker logs:**
   ```bash
   sudo journalctl -u recruitpro-worker -p err
   ```

### Issue: "ImportError in worker"

**Symptoms:**
- Worker crashes with `ImportError` or `ModuleNotFoundError`

**Solutions:**

1. **Check Python path:**
   ```bash
   # In worker service file, ensure correct path
   Environment="PATH=/path/to/venv/bin"
   WorkingDirectory=/path/to/recruitpro-codex
   ```

2. **Reinstall dependencies:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Check .env file is readable:**
   ```bash
   ls -la .env
   chmod 600 .env
   ```

---

## Application Won't Start

### Issue: "Port already in use"

**Symptoms:**
- Error: `[Errno 98] Address already in use`

**Solutions:**

1. **Find process using port:**
   ```bash
   sudo lsof -i :8000
   # or
   sudo netstat -tulpn | grep :8000
   ```

2. **Kill the process:**
   ```bash
   sudo kill -9 <PID>
   ```

3. **Use different port:**
   ```bash
   uvicorn app.main:app --port 8001
   ```

### Issue: "Module not found"

**Symptoms:**
- Error: `ModuleNotFoundError: No module named 'app'`

**Solutions:**

1. **Check working directory:**
   ```bash
   pwd
   # Should be /path/to/recruitpro-codex
   ```

2. **Check Python path:**
   ```bash
   python3 -c "import sys; print('\n'.join(sys.path))"
   ```

3. **Reinstall application:**
   ```bash
   pip install -e .
   ```

### Issue: "Permission denied"

**Symptoms:**
- Error: `PermissionError: [Errno 13] Permission denied`

**Solutions:**

1. **Check file permissions:**
   ```bash
   ls -la storage/ data/
   ```

2. **Fix permissions:**
   ```bash
   # If running as recruitpro user
   sudo chown -R recruitpro:recruitpro storage/ data/
   chmod 755 storage/ data/
   ```

3. **Check .env permissions:**
   ```bash
   chmod 600 .env
   ```

---

## Performance Issues

### Issue: "Application is slow"

**Symptoms:**
- Requests take > 5 seconds
- High CPU usage

**Solutions:**

1. **Check database performance:**
   ```sql
   -- Find slow queries
   SELECT query, mean_exec_time
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

2. **Add database indexes:**
   ```sql
   -- Check missing indexes
   SELECT schemaname, tablename, attname
   FROM pg_stats
   WHERE schemaname = 'public'
   AND n_distinct > 100;
   ```

3. **Increase workers:**
   ```bash
   # In systemd service or uvicorn command
   --workers 4
   ```

4. **Check Redis performance:**
   ```bash
   redis-cli --latency
   ```

### Issue: "High memory usage"

**Symptoms:**
- Application using > 1GB RAM
- Out of memory errors

**Solutions:**

1. **Check memory usage:**
   ```bash
   ps aux | grep uvicorn
   ps aux | grep worker.py
   ```

2. **Reduce workers:**
   ```bash
   # Use fewer uvicorn workers
   --workers 1
   ```

3. **Clear Redis cache:**
   ```bash
   redis-cli -u $REDIS_URL FLUSHDB
   ```

---

## Connection Issues

### Issue: "CORS errors in browser"

**Symptoms:**
- Browser console: `Access-Control-Allow-Origin`

**Solutions:**

1. **Add origin to .env:**
   ```bash
   RECRUITPRO_CORS_ALLOWED_ORIGINS="http://localhost:3000,https://yourdomain.com"
   ```

2. **Restart application:**
   ```bash
   sudo systemctl restart recruitpro-web
   ```

### Issue: "SSL certificate errors"

**Symptoms:**
- Error: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions:**

1. **Renew Let's Encrypt certificate:**
   ```bash
   sudo certbot renew
   sudo systemctl reload nginx
   ```

2. **Check certificate expiry:**
   ```bash
   echo | openssl s_client -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
   ```

---

## File Upload Issues

### Issue: "File upload fails"

**Symptoms:**
- Error: `413 Request Entity Too Large`
- Files > 50MB fail

**Solutions:**

1. **Increase Nginx limit:**
   ```nginx
   client_max_body_size 100M;
   ```

2. **Increase Uvicorn limit:**
   ```bash
   uvicorn app.main:app --limit-max-requests 100000
   ```

3. **Check storage permissions:**
   ```bash
   ls -la storage/
   chmod 755 storage/
   ```

### Issue: "Storage directory full"

**Symptoms:**
- Error: `[Errno 28] No space left on device`

**Solutions:**

1. **Check disk space:**
   ```bash
   df -h
   ```

2. **Clean old files:**
   ```bash
   find storage/ -name "*.pdf" -mtime +90 -delete
   ```

3. **Increase disk space:**
   - Resize volume
   - Add new volume
   - Move storage to larger disk

---

## Authentication Issues

### Issue: "Token expired"

**Symptoms:**
- Error: `401 Unauthorized`
- Error: `Token has expired`

**Solutions:**

1. **Login again:**
   - Users need to re-authenticate
   - Tokens expire after 60 minutes by default

2. **Increase token lifetime:**
   ```bash
   # In .env
   RECRUITPRO_ACCESS_TOKEN_EXPIRE_MINUTES=120
   ```

### Issue: "Invalid credentials"

**Symptoms:**
- Login fails with correct password

**Solutions:**

1. **Reset password via database:**
   ```bash
   python3 -c "
   from app.database import get_session
   from app.models import User
   from passlib.context import CryptContext

   pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

   with get_session() as db:
       user = db.query(User).filter(User.email == 'admin@example.com').first()
       if user:
           user.password_hash = pwd_context.hash('newpassword')
           db.commit()
           print('Password reset successfully')
   "
   ```

---

## Quick Reference: Restart All Services

```bash
# Systemd
sudo systemctl restart recruitpro-web recruitpro-worker

# Docker
docker-compose restart

# Manual (tmux)
tmux kill-session -t recruitpro
# Then start new session
```

---

## Getting More Help

1. **Check logs first:**
   ```bash
   sudo journalctl -u recruitpro-web -n 100
   sudo journalctl -u recruitpro-worker -n 100
   ```

2. **Test each component:**
   - Database: `psql $RECRUITPRO_DATABASE_URL -c "SELECT 1"`
   - Redis: `redis-cli -u $REDIS_URL ping`
   - Gemini: Test with curl (see above)

3. **Health check:**
   ```bash
   curl http://localhost:8000/api/health | jq
   ```

4. **Enable debug logging:**
   ```bash
   # In .env
   LOG_LEVEL=DEBUG

   # Restart
   sudo systemctl restart recruitpro-web recruitpro-worker
   ```

---

## Common Error Messages & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Service not running | Start service |
| `Module not found` | Missing dependencies | `pip install -r requirements.txt` |
| `Permission denied` | Wrong file permissions | `chmod` or `chown` files |
| `Port already in use` | Process using port | Kill process or use different port |
| `Database connection failed` | Wrong credentials | Check `DATABASE_URL` |
| `Redis connection failed` | Redis not running | Start Redis |
| `Gemini API key invalid` | Wrong/missing key | Check `GEMINI_API_KEY` |
| `429 Too Many Requests` | API quota exceeded | Wait or upgrade plan |
| `Certificate verify failed` | SSL issues | Renew certificate |
| `Out of memory` | Too many workers | Reduce workers |

---

## Still Having Issues?

1. Collect diagnostic information:
   ```bash
   curl http://localhost:8000/api/health > health.json
   sudo journalctl -u recruitpro-web -n 500 > web.log
   sudo journalctl -u recruitpro-worker -n 500 > worker.log
   ```

2. Check configuration:
   ```bash
   grep -v "SECRET\|KEY\|PASSWORD" .env > config_sanitized.txt
   ```

3. Review the logs for specific error messages and search for solutions

---

**Remember:** Most issues can be resolved by:
1. Checking logs
2. Verifying configuration (.env)
3. Restarting services
4. Testing individual components
