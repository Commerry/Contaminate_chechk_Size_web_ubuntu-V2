module.exports = {
  apps: [
    {
      name: 'pse-vision-backend',
      script: 'python_scripts/backend_server.py',
      interpreter: 'venv/bin/python',
      cwd: './',  // Use current directory
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      error_file: 'logs/pm2-backend-error.log',
      out_file: 'logs/pm2-backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      time: true
    }
  ]
};
