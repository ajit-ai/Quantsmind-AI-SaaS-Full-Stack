import { Controller, Get } from "@nestjs/common";

@Controller("health")
export class HealthController {
  @Get()
  health() {
    return { status: "ok", uptime: process.uptime(), db: "pending", redis: "pending", ai: "pending" };
  }
  @Get("ready")
  ready() {
    return { status: "ready" };
  }
  @Get("live")
  live() {
    return { status: "live" };
  }
}
