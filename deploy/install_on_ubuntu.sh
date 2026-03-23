#!/usr/bin/env bash
# Redirects to the canonical installer at the repository root.
exec "$(dirname "$0")/../install.sh" "$@"

echo "Install complete."
echo "Next steps:"
echo "  1) Configure catt aliases as $SERVICE_USER (equipment, secondary)."
echo "  2) Run manual test: sudo -u $SERVICE_USER $PROJECT_ROOT/scripts/cast_dashboards.sh"
echo "  3) Check logs: sudo tail -f /var/log/connectcatt/cast.log"
