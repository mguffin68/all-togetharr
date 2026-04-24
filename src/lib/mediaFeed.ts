import prisma from "@/lib/prisma";

export async function getMediaFeed(service: string) {
  const data: Record<string, unknown> = {};

  switch (service) {
    case "sonarr": {
      const health = await prisma.connection.findFirst({
        where: { service: { name: "Sonarr" }, baseUrl: { not: null } },
        select: { baseUrl: true, apiKey: true },
      });
      if (!health) {
        return { series: [] };
      }
      return data;
    }
    case "radarr": {
      const health = await prisma.connection.findFirst({
        where: { service: { name: "Radarr" }, baseUrl: { not: null } },
        select: { baseUrl: true, apiKey: true },
      });
      if (!health) {
        return { movies: [] };
      }
      return data;
    }
    default:
      return {};
  }
}
