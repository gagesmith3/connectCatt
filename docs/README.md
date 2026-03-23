# connectCatt TV Dashboard Automation

This project auto-casts two Apache dashboard pages to two TVs using the open-source `catt` tool.

## Scope

- TV alias `equipment` -> `http://192.168.1.6:8080/EQUIP/equipment-tv.php`
- TV alias `secondary` -> `http://192.168.1.6:8080/SECONDARY/TrimmingDashboard.php`
- Schedule: Monday-Friday at 07:55
- Runtime target: Ubuntu VM

## Files

- `scripts/cast_dashboards.sh`: main casting script with retries, lock, and logs
- `deploy/connectcatt.cron`: cron schedule definition
- `deploy/connectcatt.logrotate`: log rotation policy
- `deploy/install_on_ubuntu.sh`: helper installer for Ubuntu

## One-time setup on Ubuntu VM

1. Copy this repository to the VM.
2. From the repository root, run:

```bash
chmod +x deploy/install_on_ubuntu.sh scripts/cast_dashboards.sh
./deploy/install_on_ubuntu.sh
```

### Install directly from GitHub (no git clone required)

Set your repository raw base and run the installer directly:

```bash
export GITHUB_RAW_BASE="https://raw.githubusercontent.com/<owner>/<repo>/<branch>"
curl -fsSL "$GITHUB_RAW_BASE/deploy/install_on_ubuntu.sh" -o /tmp/install_on_ubuntu.sh
chmod +x /tmp/install_on_ubuntu.sh
/tmp/install_on_ubuntu.sh
```

3. Configure `catt` aliases as the service user:

```bash
sudo -u connectcatt catt ls
sudo -u connectcatt catt -d "Equipment" status
sudo -u connectcatt catt -d "Secondary" status
```

If aliases are not already configured, create or edit `~connectcatt/.config/catt/catt.cfg` with device aliases.

Example:

```ini
[aliases]
equipment = Equipment
secondary = Secondary
```

## Manual test

```bash
sudo -u connectcatt /opt/connectcatt/scripts/cast_dashboards.sh
sudo tail -n 100 /var/log/connectcatt/cast.log
```

## Cron verification

```bash
sudo cat /etc/cron.d/connectcatt
sudo systemctl status cron
```

## Troubleshooting

- Device not found:
  - Verify Chromecast names and aliases.
  - Check VM and TVs are on the same network/VLAN.
- URL unreachable:
  - Test from VM with `curl -I <url>`.
  - Confirm Apache is serving from VM network context.
- No scheduled run:
  - Verify VM timezone using `timedatectl`.
  - Confirm cron service is running.

## Notes

- Script prevents overlapping runs with a lock file.
- Script exits non-zero on any TV failure so monitoring can detect issues.
- Logs are written to `/var/log/connectcatt/cast.log`.
