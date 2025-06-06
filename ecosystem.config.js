module.exports = {
  "apps": [{
    "name": "quant-minimal",
    "script": "minimal_quantitative_service.py",
    "cwd": "/root/VNPY",
    "interpreter": "python3",
    "instances": 1,
    "exec_mode": "fork",
    "watch": false,
    "max_memory_restart": "1G",
    "env": {
      "NODE_ENV": "production"
    },
    "error_file": "/root/.pm2/logs/quant-minimal-error.log",
    "out_file": "/root/.pm2/logs/quant-minimal-out.log",
    "log_file": "/root/.pm2/logs/quant-minimal.log",
    "pid_file": "/root/.pm2/pids/quant-minimal.pid",
    "restart_delay": 4000,
    "min_uptime": "10s",
    "max_restarts": 10
  }]
}; 