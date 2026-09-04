import { Plus } from "lucide-react";

export function ModuleHeader({ title, onAdd, addLabel = "New", testid }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <p className="text-sm font-semibold text-muted-foreground">{title}</p>
      {onAdd && (
        <button onClick={onAdd} data-testid={testid}
          className="flex items-center gap-1.5 rounded-full bg-brand px-3.5 py-2 text-sm font-semibold text-white active:scale-95">
          <Plus className="h-4 w-4" /> {addLabel}
        </button>
      )}
    </div>
  );
}
