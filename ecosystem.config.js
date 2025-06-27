module.exports = {
  "apps": [
    {
      "name": "quant-backend",
      "script": "quantitative_service.py",
      "cwd": "/root/VNPY",
      "interpreter": "/root/VNPY/venv/bin/python",
      "instances": 1,
      "exec_mode": "fork",
      "watch": false,
      "max_memory_restart": "2G",
      "env": {
        "NODE_ENV": "production",
        "PYTHONPATH": "/root/VNPY",
        "PYTHONUNBUFFERED": "1"
      },
      "error_file": "/root/.pm2/logs/quant-backend-error.log",
      "out_file": "/root/.pm2/logs/quant-backend-out.log",
      "log_file": "/root/.pm2/logs/quant-backend.log",
      "pid_file": "/root/.pm2/pids/quant-backend.pid",
      "restart_delay": 4000,
      "min_uptime": "10s",
      "max_restarts": 15,
      "autorestart": true,
      "kill_timeout": 1600
    },
    {
      "name": "quant-frontend",
      "script": "web_app.py",
      "cwd": "/root/VNPY",
      "interpreter": "/root/VNPY/venv/bin/python",
      "instances": 1,
      "exec_mode": "fork",
      "watch": false,
      "max_memory_restart": "1G",
      "env": {
        "NODE_ENV": "production",
        "PYTHONPATH": "/root/VNPY",
        "PYTHONUNBUFFERED": "1",
        "FLASK_ENV": "production"
      },
      "error_file": "/root/.pm2/logs/quant-frontend-error.log",
      "out_file": "/root/.pm2/logs/quant-frontend-out.log",
      "log_file": "/root/.pm2/logs/quant-frontend.log",
      "pid_file": "/root/.pm2/pids/quant-frontend.pid",
      "restart_delay": 4000,
      "min_uptime": "10s",
      "max_restarts": 15,
      "autorestart": true,
      "kill_timeout": 1600
    }
  ]
}; 