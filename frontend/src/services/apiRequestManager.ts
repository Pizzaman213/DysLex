export class ApiRequestManager {
  private controllers: Map<string, AbortController> = new Map();

  startRequest(key: string): AbortSignal {
    this.cancelRequest(key); // Cancel any existing request with same key
    const controller = new AbortController();
    this.controllers.set(key, controller);
    return controller.signal;
  }

  cancelRequest(key: string): void {
    const controller = this.controllers.get(key);
    if (controller) {
      controller.abort();
      this.controllers.delete(key);
    }
  }

  cancelAll(): void {
    this.controllers.forEach(controller => controller.abort());
    this.controllers.clear();
  }
}

export const apiRequestManager = new ApiRequestManager();
