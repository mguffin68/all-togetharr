import prisma from "@/lib/prisma";

export async function getServicesWithConnections() {
  return prisma.service.findMany({
    include: {
      connections: {
        include: {
          categories: true,
        },
        orderBy: {
          createdAt: "desc",
        },
      },
    },
    orderBy: {
      updatedAt: "desc",
    },
  });
}

export async function getServiceById(id: string) {
  return prisma.service.findUnique({
    where: { id },
    include: {
      connections: {
        include: {
          categories: true,
        },
      },
    },
  });
}

export async function createService(
  name: string,
  type: string,
  enabled?: boolean
) {
  return prisma.service.create({
    data: {
      name,
      type,
      enabled: enabled ?? true,
      connections: {
        create: [
          {
            label: "Default",
            baseUrl: "",
            apiKey: "",
            healthStatus: "unknown",
          },
        ],
      },
    },
    include: {
      connections: true,
    },
  });
}

export async function deleteService(id: string) {
  return prisma.service.delete({
    where: { id },
  });
}

export async function updateService(id: string, data: object) {
  return prisma.service.update({
    where: { id },
    data,
  });
}

export async function getHealthSummary() {
  return prisma.service.findMany({
    include: {
      connections: {
        select: {
          serviceId: true,
          service: {
            select: {
              id: true,
              name: true,
              type: true,
              enabled: true,
              connections: {
                select: {
                  healthStatus: true,
                  baseUrl: true,
                },
                take: 1,
              },
            },
          },
        },
      },
    },
  });
}

export async function saveSetting(key: string, value: string) {
  return prisma.settings.upsert({
    where: { key },
    update: { value },
    create: { key, value },
  });
}

export async function getSetting(key: string) {
  return prisma.settings.findUnique({
    where: { key },
  });
}
