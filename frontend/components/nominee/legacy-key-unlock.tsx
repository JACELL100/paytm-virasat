"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { toast } from "sonner";
import { KeyRound, QrCode, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useUnlockVault } from "@/lib/queries/nominee";

const Scanner = dynamic(
  () => import("@yudiel/react-qr-scanner").then((m) => m.Scanner),
  { ssr: false },
);

export function LegacyKeyUnlock({ vaultId }: { vaultId: string }) {
  const unlock = useUnlockVault(vaultId);
  const [share, setShare] = useState("");
  const [scanOpen, setScanOpen] = useState(false);

  async function handleUnlock(value: string) {
    if (!value.trim()) return;
    try {
      await unlock.mutateAsync(value);
      toast.success("Your family's Virasat is unlocked");
    } catch {
      toast.message("Backend not reachable yet — unlock will work once it's live.");
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          value={share}
          onChange={(e) => setShare(e.target.value)}
          placeholder="Paste your Legacy Key"
          className="font-mono-tabular"
        />
        <Button variant="brand" onClick={() => handleUnlock(share)} disabled={unlock.isPending}>
          {unlock.isPending ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}
          Unlock
        </Button>
      </div>
      <Dialog open={scanOpen} onOpenChange={setScanOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" className="w-full">
            <QrCode className="size-4" /> Scan Legacy Key QR instead
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Scan your Legacy Key</DialogTitle>
          </DialogHeader>
          <div className="overflow-hidden rounded-xl">
            {scanOpen && (
              <Scanner
                onScan={(codes) => {
                  const value = codes[0]?.rawValue;
                  if (value) {
                    setShare(value);
                    setScanOpen(false);
                    handleUnlock(value);
                  }
                }}
                onError={() => toast.error("Couldn't access the camera")}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
