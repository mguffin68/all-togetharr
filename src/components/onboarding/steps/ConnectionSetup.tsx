import { useOnboardingStore } from "@/stores/useOnboardingStore";
import { useServicesStore } from "@/stores/useServicesStore";
import Icon from "@/components/ui/Icon";

export default function ConnectionSetup() {
  const selectedServices = useOnboardingStore((s) => s.selectedServices);
  const goToStep = useOnboardingStore((s) => s.goToStep);
  const updateServiceConfig = useOnboardingStore((s) => s.updateServiceConfig);
  const markCompleted = useOnboardingStore((s) => s.markCompleted);
  const addService = useServicesStore((s) => s.addService);

  const handleComplete = () => {
    selectedServices.forEach((service) => {
      addService({
        name: service.name,
        type: service.type,
        enabled: true,
        status: "unknown",
      });
    });
    markCompleted();
  };

  return (
    <div>
      <div className="mb-12 text-center">
        <h1 className="text-4xl md:text-5xl font-extrabold text-on-surface tracking-[-0.02em] mb-4">
          Configure Your Services.
        </h1>
        <p className="text-on-surface-variant text-lg max-w-xl mx-auto leading-relaxed">
          Enter the connection details for each selected service. Everything is stored
          locally on your machine.
        </p>
      </div>

      {selectedServices.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 text-on-surface-variant">
          <p className="text-sm">No services selected. Go back to choose some.</p>
        </div>
      ) : (
        <div className="space-y-8 mb-12">
          {selectedServices.map((service) => (
            <div
              key={service.name}
              className="bg-surface-container-low rounded-xl p-8 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 p-8 opacity-10">
                <Icon name="tune" size={72} />
              </div>
              <div className="relative z-10 max-w-2xl">
                <header className="mb-8">
                  <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-1 flex items-center gap-3">
                    <Icon name={service.icon} size={24} className="text-primary" />
                    {service.name}
                  </h2>
                  <p className="text-on-surface-variant">{service.description}</p>
                </header>

                <div className="space-y-6">
                  <div>
                    <label className="block text-xs uppercase tracking-[0.1em] font-bold text-on-surface-variant mb-2">
                      Local IP/URL
                    </label>
                    <input
                      className="w-full bg-transparent border-t-0 border-x-0 border-b border-outline-variant/20 focus:border-primary focus:ring-0 text-on-surface text-lg py-2 transition-all duration-300 placeholder:text-outline-variant/40"
                      placeholder={`http://192.168.1.100:8989`}
                      type="text"
                      value={service.baseUrl ?? ""}
                      onChange={(e) =>
                        updateServiceConfig(service.name, {
                          baseUrl: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-[0.1em] font-bold text-on-surface-variant mb-2">
                      API Key / Token
                    </label>
                    <input
                      className="w-full bg-transparent border-t-0 border-x-0 border-b border-outline-variant/20 focus:border-primary focus:ring-0 text-on-surface text-lg py-2 transition-all duration-300 placeholder:text-outline-variant/40"
                      placeholder="••••••••••••••••••••••••"
                      type="password"
                      value={service.apiKey ?? ""}
                      onChange={(e) =>
                        updateServiceConfig(service.name, {
                          apiKey: e.target.value,
                        })
                      }
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-col md:flex-row items-center justify-between gap-6 pt-6 border-t border-surface-container">
        <button
          type="button"
          onClick={() => goToStep("services")}
          className="text-on-surface-variant hover:text-on-surface font-medium transition-colors flex items-center gap-2"
        >
          <Icon name="arrow_back" size={16} />
          Previous Step
        </button>
        <div className="flex gap-4">
          <button
            type="button"
            onClick={handleComplete}
            className="px-8 py-3 rounded-full bg-surface-container-high text-on-surface-variant font-bold hover:bg-surface-container-highest transition-all"
          >
            Skip for Now
          </button>
          <button
            type="button"
            disabled={selectedServices.length === 0}
            onClick={handleComplete}
            className="px-12 py-3 rounded-full bg-primary text-on-primary font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            Next: Dashboard Sync
          </button>
        </div>
      </div>
    </div>
  );
}
