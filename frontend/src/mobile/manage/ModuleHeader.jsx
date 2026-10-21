import { Plus } from "lucide-react";

export function ModuleHeader({ title, onAdd, addLabel = "New", testid }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <p className="text-sm font-semibold text-muted-foreground">{title}</p>
      {onAdd && (
        <button onClick={onAdd} data-testid={testid}
          className="flex min-h-[40px] items-center gap-1.5 rounded-full bg-foreground px-4 py-2 text-sm font-semibold text-background transition-transform active:scale-95">
          <Plus className="h-4 w-4" /> {addLabel}
        </button>
      )}
    </div>
  );
}
