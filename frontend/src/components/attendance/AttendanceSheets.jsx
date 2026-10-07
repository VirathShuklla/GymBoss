import { useState } from "react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { usePublicConfig, waLink } from "../../hooks/usePublicConfig";
import { QrPanel } from "./QrPanel";
import { BiometricPanel } from "./BiometricPanel";
import { ConnectDeviceForm, SetupGuide, SupportedDevices, TestPunchForm } from "./DeviceForms";

// All QR / biometric sheets. `Sheet` is BottomSheet on mobile, WebSheet (dialog) on web.
export function AttendanceSheets({ Sheet, sheet, setSheet, data }) {
  const { qr, devices, types, reload } = data;
  const { outlets } = useAuth();
  const config = usePublicConfig();
  const [testDevice, setTestDevice] = useState(null);
  const close = (o) => !o && setSheet(null);
  const contactHref = config?.whatsapp_number
    ? waLink(config.whatsapp_number, "Hi, I need help connecting my biometric device to GymBoss_VVO.")
    : config?.support_email ? `mailto:${config.support_email}?subject=Biometric device setup` : null;

  const call = async (fn, ok) => {
    try { await fn(); if (ok) toast.success(ok); reload(); } catch (e) { toast.error(apiError(e)); }
  };
  const toggleAuto = (d, v) => call(() => api.put(`/attendance/devices/${d.id}`, { auto_delete_on_expiry: v }), v ? "Expired members will be removed from this device" : "Auto delete turned off");
  const remove = (d) => window.confirm(`Remove ${d.name}? Past attendance stays saved.`) && call(() => api.delete(`/attendance/devices/${d.id}`), "Device removed");
  const rotate = (outletId) => window.confirm("Generate a new QR? The old printed QR will stop working.") && call(() => api.post(`/attendance/qr/${outletId}/rotate`), "New QR generated. Print and replace the old one.");

  return (
    <>
      <Sheet open={sheet === "qr"} onOpenChange={close} title="Attendance QR" subtitle="Let members and staff check in by scanning this code" testid="att-qr-sheet">
        <QrPanel qr={qr} onRotate={rotate} />
      </Sheet>
      <Sheet open={sheet === "bio"} onOpenChange={close} title="Biometric Attendance" subtitle="Connect and manage fingerprint devices for your gym" testid="att-bio-sheet">
        <BiometricPanel devices={devices} onOpen={setSheet} onToggleAuto={toggleAuto} onRemove={remove} onRefresh={reload}
          onTest={(d) => { setTestDevice(d); setSheet("test"); }} contactHref={contactHref} />
      </Sheet>
      <Sheet open={sheet === "connect"} onOpenChange={close} title="Connect a Device" subtitle="Enter your device details to connect it to your gym" testid="att-connect-sheet">
        <ConnectDeviceForm types={types} outlets={outlets} contactHref={contactHref} onDone={() => { reload(); setSheet("bio"); }} />
      </Sheet>
      <Sheet open={sheet === "guide"} onOpenChange={close} title="Setup Guide" subtitle="Connect your eSSL / ZKTeco machine in 5 steps" testid="att-guide-sheet">
        <SetupGuide />
      </Sheet>
      <Sheet open={sheet === "supported"} onOpenChange={close} title="Supported Devices" testid="att-supported-sheet">
        <SupportedDevices types={types} />
      </Sheet>
      <Sheet open={sheet === "test" && !!testDevice} onOpenChange={close} title="Test punch" subtitle={`Simulate a fingerprint scan on ${testDevice?.name || "device"}`} testid="att-test-sheet">
        {testDevice && <TestPunchForm device={testDevice} onDone={() => { reload(); setSheet("bio"); }} />}
      </Sheet>
    </>
  );
}
