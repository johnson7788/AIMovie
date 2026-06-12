import { buildApiUrl } from '@/common/apiBaseUrl';
import { $http } from '@/common/http';

export interface SSEEvent {
    type: string;
    stage?: string;
    message?: string;
    file_type?: string;
    file_path?: string;
    url?: string;
    content_preview?: string;
    error?: string;
    result?: string;
    level?: string;
    current?: number;
    total?: number;
    percent?: number;
    timestamp?: number;
    duration_ms?: number;
    scene_count?: number;
    shot_count?: number;
    character_count?: number;
    shot_idx?: number;
    frame_type?: string;
    character_name?: string;
    view?: string;
    scene_index?: number;
    total_scenes?: number;
}

export interface UseSSEOptions {
    onEvent?: (event: SSEEvent) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
}

export function useSSE() {
    let abortController: AbortController | null = null;

    const connect = (taskId: string, options: UseSSEOptions) => {
        const url = buildApiUrl(`api/tasks/${taskId}/stream`);
        abortController = new AbortController();

        fetch(url, {
            signal: abortController.signal,
            headers: $http.getHeaders(),
        })
            .then(async (response) => {
                if (!response.ok) {
                    options.onError?.(new Error(`HTTP ${response.status}: ${response.statusText}`));
                    return;
                }
                const reader = response.body?.getReader();
                if (!reader) {
                    options.onError?.(new Error('No response body'));
                    return;
                }
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        options.onComplete?.();
                        break;
                    }
                    buffer += decoder.decode(value, { stream: true });
                    const parts = buffer.split('\n\n');
                    buffer = parts.pop() || '';
                    for (const part of parts) {
                        const lines = part.split('\n');
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const event: SSEEvent = JSON.parse(line.substring(6));
                                    options.onEvent?.(event);
                                    if (event.type === 'complete' || event.type === 'error') {
                                        options.onComplete?.();
                                        return;
                                    }
                                } catch {
                                    // skip malformed JSON events
                                }
                            }
                        }
                    }
                }
            })
            .catch((err: Error) => {
                if (err.name !== 'AbortError') {
                    options.onError?.(err);
                }
            });
    };

    const disconnect = () => {
        abortController?.abort();
        abortController = null;
    };

    return { connect, disconnect };
}
