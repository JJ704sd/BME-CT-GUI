// createInferenceEventSource：把后端 /api/segment/jobs/{id}/events 的 SSE 流
// 包成一个带指数退避重试的 EventSource 句柄。
//
// 背景：浏览器原生 EventSource 在连接断开时会触发 onerror，但默认是 3 秒一次
// 重连且无上限；BME 竞赛答辩现场最常见的翻车就是网络抖动 1-2 秒后浏览器显示
// "推理失败"。这里手动重试，按 200ms→2s 指数退避，最多 3 次；3 次失败后
// 调用 onfatal 让上层 reject。
//
// 调用方约定：
//   1. onmessage 与原生 EventSource 行为一致（每条 `data: ...` 触发一次）。
//   2. 收到 `event: complete` 等终止事件时，调用方必须主动调用 handle.close()
//      阻止继续重试。
//   3. onretry 在每次重试前触发一次，便于 UI 提示"正在重连"。
//   4. onfatal 在 3 次重试耗尽时触发一次，由调用方决定如何 reject Promise。
//
// 这个模块纯前端，没有外部依赖。

export type CreateInferenceEventSourceOptions = {
  url: string;
  onmessage: (event: MessageEvent) => void;
  onretry?: (info: { retryCount: number; nextDelayMs: number }) => void;
  onfatal?: (info: { retryCount: number }) => void;
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
};

export type InferenceEventSourceHandle = {
  readonly retryCount: number;
  close: () => void;
};

export const DEFAULT_INFERENCE_EVENT_SOURCE_MAX_RETRIES = 3;
export const DEFAULT_INFERENCE_EVENT_SOURCE_BASE_DELAY_MS = 200;
export const DEFAULT_INFERENCE_EVENT_SOURCE_MAX_DELAY_MS = 2000;

export function createInferenceEventSource(options: CreateInferenceEventSourceOptions): InferenceEventSourceHandle {
  const maxRetries = options.maxRetries ?? DEFAULT_INFERENCE_EVENT_SOURCE_MAX_RETRIES;
  const baseDelayMs = options.baseDelayMs ?? DEFAULT_INFERENCE_EVENT_SOURCE_BASE_DELAY_MS;
  const maxDelayMs = options.maxDelayMs ?? DEFAULT_INFERENCE_EVENT_SOURCE_MAX_DELAY_MS;
  let retryCount = 0;
  let current: EventSource | null = null;
  let closedByConsumer = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  function clearRetryTimer() {
    if (retryTimer !== null) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
  }

  function open() {
    if (closedByConsumer) return;
    const es = new EventSource(options.url);
    current = es;
    es.onmessage = options.onmessage;
    es.onerror = (err) => {
      if (closedByConsumer) return;
      es.close();
      current = null;
      if (retryCount >= maxRetries) {
        options.onfatal?.({ retryCount });
        return;
      }
      const nextDelayMs = Math.min(maxDelayMs, baseDelayMs * Math.pow(2, retryCount));
      retryCount += 1;
      options.onretry?.({ retryCount, nextDelayMs });
      retryTimer = setTimeout(() => {
        retryTimer = null;
        open();
      }, nextDelayMs);
    };
  }

  open();

  return {
    get retryCount() {
      return retryCount;
    },
    close() {
      closedByConsumer = true;
      clearRetryTimer();
      if (current) {
        current.close();
        current = null;
      }
    },
  };
}
