import { NextResponse } from "next/server";
import { proxyRequest, checkHealth } from "@/lib/proxy";
import prisma from "@/lib/prisma";

export async function GET(
  request: Request,
  context: { params: { service: string; path: string[] } }
) {
  try {
    const { service, path } = context.params;

    const connection = await prisma.connection.findFirst({
      where: {
        service: { name: service },
        baseUrl: { not: "", not: null },
      },
      include: {
        service: true,
      },
    });

    if (!connection) {
      return NextResponse.json(
        { error: `No active connection found for service: ${service}` },
        { status: 404 }
      );
    }

    const target = `/${path.join("/")}`;
    const result = await proxyRequest(connection.baseUrl, target, connection.apiKey, {
      service,
      path: [],
    });

    return NextResponse.json(result.data);
  } catch (error) {
    return NextResponse.json(
      { error: "Proxy request failed" },
      { status: 500 }
    );
  }
}
