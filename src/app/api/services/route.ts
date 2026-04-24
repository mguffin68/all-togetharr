import { NextResponse } from "next/server";
import { z } from "zod";
import prisma from "@/lib/prisma";
import { getServiceById, getServicesWithConnections, createService, deleteService, updateService } from "@/lib/db";

const payloadSchema = z.object({
  name: z.string().min(1),
  type: z.string(),
  baseUrl: z.string().url().optional(),
  apiKey: z.string(),
  port: z.number().optional(),
  label: z.string().default("Default"),
  categories: z.array(z.string()).optional(),
  rootPath: z.string().optional(),
  protocol: z.string().optional(),
});

export async function GET() {
  try {
    const services = await getServicesWithConnections();
    const simplified = services.map(({ connections, ...service }) => (
      {
        ...service,
        connectionCount: connections.length,
      }
    ));
    return NextResponse.json(simplified);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch services" },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const validation = payloadSchema.safeParse(body);

    if (!validation.success) {
      return NextResponse.json(
        { error: "Invalid payload", details: validation.error.errors },
        { status: 400 }
      );
    }

    const { name, type, baseUrl, apiKey, port, label, categories, rootPath, protocol } = validation.data;

    const service = await createService(name, type);

    const connection = await prisma.connection.create({
      data: {
        serviceId: service.id,
        label: label || "Default",
        baseUrl: baseUrl || "",
        apiKey,
        apiVersion: undefined,
        healthStatus: "unknown",
        ...(categories
          ? {
              categories: {
                create: categories.map((catName: string) => ({
                  name: catName,
                  rootPath: rootPath,
                  protocol,
                })),
              },
            }
          : {}),
      },
    });

    const fullService = await getServiceById(service.id);
    return NextResponse.json(fullService);
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to create service" },
      { status: 500 }
    );
  }
}

export async function PUT(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");

    if (!id) {
      return NextResponse.json(
        { error: "Missing service ID" },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { name, type, enabled } = payloadSchema.partial().parse(body);

    const service = await updateService(id, { name, type, enabled });
    return NextResponse.json(service);
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to update service" },
      { status: 500 }
    );
  }
}

export async function DELETE(_request: Request, context: { params: { id: string } }) {
  try {
    const { id } = context.params;
    await deleteService(id);
    return NextResponse.json({ success: true });
  } catch {
    return NextResponse.json(
      { error: "Failed to delete service" },
      { status: 500 }
    );
  }
}
