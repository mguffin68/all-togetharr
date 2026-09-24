import { useOnboardingStore } from "@/stores/useOnboardingStore";
import { SERVICE_OPTIONS } from "@/services/serviceRegistry";
import Icon from "@/components/ui/Icon";

export default function ServiceSelection() {
  const selectedServices = useOnboardingStore((s) => s.selectedServices);
  const selectService = useOnboardingStore((s) => s.selectService);
  const deselectService = useOnboardingStore((s) => s.deselectService);
  const goToStep = useOnboardingStore((s) => s.goToStep);

  return (
    <div>
      <div className="mb-12 text-center">
        <h1 className="text-4xl md:text-5xl font-extrabold text-on-surface tracking-[-0.02em] mb-4">
          Connect Your Core.
        </h1>
        <p className="text-on-surface-variant text-lg max-w-xl mx-auto leading-relaxed">
          Select the services you want to integrate. We&apos;ll curate them into a
          single, seamless editorial experience.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        {SERVICE_OPTIONS.map((service) => {
          const selected = selectedServices.some((s) => s.name === service.name);
          return (
            <button
              key={service.name}
              type="button"
              onClick={() =>
                selected
                  ? deselectService(service.name)
                  : selectService({
                      name: service.name,
                      type: service.type,
                      icon: service.icon,
                      description: service.description,
                    })
              }
              className={`group relative aspect-square rounded-xl p-6 transition-all duration-300 cursor-pointer ${
                selected
                  ? "bg-white border-2 border-primary-fixed-dim shadow-2xl shadow-[#2D3338]/5"
                  : "bg-surface-container-lowest ring-2 ring-transparent hover:bg-surface-container hover:shadow-2xl hover:shadow-[#2D3338]/5 hover:ring-primary-fixed-dim"
              }`}
            >
              <div className="h-full flex flex-col justify-between">
                <Icon name={service.icon} size={32} className="text-primary" fill={selected} />
                <div>
                  <span className="block font-bold text-on-surface tracking-tight">
                    {service.name}
                  </span>
                  <span className="text-xs uppercase tracking-[0.1em] text-on-surface-variant font-medium">
                    {service.description}
                  </span>
                </div>
              </div>
              <div
                className={`absolute top-4 right-4 transition-opacity ${
                  selected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                }`}
              >
                <div className="bg-primary text-on-primary rounded-full p-1 flex items-center justify-center">
                  <Icon name="check" size={14} fill />
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          disabled={selectedServices.length === 0}
          onClick={() => goToStep("configure")}
          className="px-12 py-3 rounded-full bg-primary text-on-primary font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          Next: Configure
        </button>
      </div>
    </div>
  );
}
