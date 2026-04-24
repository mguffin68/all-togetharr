import { NextResponse } from "next/server";
import prisma from "@/lib/prisma";
import { checkHealth } from "@/lib/proxy";
import { SERVICE_CATEGORIES, HEALTH_STATUS } from "@/services/serviceRegistry";

export async function GET() {
  try {
    const services = await prisma.service.findMany({
      include: {
        connections: {
          orderBy: { createdAt: "desc" },
        },
      },
    });

    const healthItems = [];

    for (const service of services) {
      const enabledConnection = service.connections.find((c) => c.baseUrl);

      if (!enabledConnection) {
        healthItems.push({
          name: service.name,
          status: HEALTH_STATUS.UNKNOWN,
        });
        continue;
      }

      const serviceConfig = SERVICE_CATEGORIES[service.name as keyof typeof SERVICE_CATEGORIES];
      const healthPath = serviceConfig?.healthPath || "/";

      const health = await checkHealth(
        enabledConnection.baseUrl,
        enabledConnection.apiKey,
        healthPath
      );

      healthItems.push({
        id: service.id,
        name: service.name,
        status: health.ok ? HEALTH_STATUS.ONLINE : HEALTH_STATUS.ERROR,
        icon: serviceConfig?.icon || "warning",
      });
    }

    return NextResponse.json({ services: healthItems });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch services" },
      { status: 500 }
    );
  }
}
