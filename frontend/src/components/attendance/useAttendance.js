import { useCallback, useEffect, useState } from "react";
import api from "../../lib/api";

export function useAttendance(outletId) {
  const [state, setState] = useState({ summary: null, qr: null, devices: null, types: [], today: null, staff: null });

  const reload = useCallback(async () => {
    const [s, q, d, t, st] = await Promise.allSettled([
      api.get("/attendance/summary"),
      api.get("/attendance/qr"),
      api.get("/attendance/devices"),
      api.get("/attendance", { params: { outlet_id: outletId || undefined } }),
      api.get("/attendance/staff"),
    ]);
    const val = (r, fb) => (r.status === "fulfilled" ? r.value.data : fb);
    const dev = val(d, { devices: [], device_types: [] });
    setState({
      summary: val(s, {}), qr: val(q, null), devices: dev.devices, types: dev.device_types,
      today: val(t, []), staff: val(st, []),
    });
  }, [outletId]);

  useEffect(() => { reload(); }, [reload]);
  return { ...state, reload };
}
