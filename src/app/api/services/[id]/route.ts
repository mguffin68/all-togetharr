import { NextResponse } from "next/server";
import prisma from "@/lib/prisma";

export async function GET(
  _request: Request,
  context: { params: { id: string } }
) {
  try {
    const { id } = context.params;
    const service = await prisma.service.findUnique({
      where: { id },
      include: {
        connections: {
          include: {
            categories: true,
          },
        },
      },
    });

    if (!service) {
      return NextResponse.json(
        { error: "Service not found" },
        { status: 404 }
      );
    }

    return NextResponse.json(service);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch service" },
      { status: 500 }
    );
  }
}

export async function PATCH(
  request: Request,
  context: { params: { id: string } }
) {
  try {
    const { id } = context.params;
    const body = await request.json();

    const service = await prisma.service.update({
      where: { id },
      data: body,
    });

    return NextResponse.json(service);
  } catch {
    return NextResponse.json(
      { error: "Failed to update service" },
      { status: 500 }
    );
  }
}
