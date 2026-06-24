import { NextResponse } from "next/server";
import { roomService, sipClient } from "@/lib/server-utils";
import { getErrorMessage } from "@/lib/error-message";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const [trunks, rules, rooms] = await Promise.all([
      sipClient.listSipInboundTrunk(),
      sipClient.listSipDispatchRule(),
      roomService.listRooms(),
    ]);

    const inboundRooms = rooms
      .filter((room) => room.name.startsWith("inbound-"))
      .map((room) => ({
        name: room.name,
        participants: room.numParticipants,
      }));

    return NextResponse.json({
      workerName: "inbound-caller",
      trunks: trunks.map((trunk) => ({
        id: trunk.sipTrunkId,
        name: trunk.name,
        numbers: trunk.numbers,
      })),
      rules: rules.map((rule) => ({
        id: rule.sipDispatchRuleId,
        name: rule.name,
        trunkIds: rule.trunkIds,
        agentNames: rule.roomConfig?.agents?.map((agent) => agent.agentName) ?? [],
      })),
      activeRooms: inboundRooms,
    });
  } catch (error: unknown) {
    return NextResponse.json({ error: getErrorMessage(error) }, { status: 500 });
  }
}
