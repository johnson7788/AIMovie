import { ClipExporter, ClipOptions } from '@/common/av-cliper/ClipExporter';
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { AxiosProgressEvent } from 'axios';
export const COMPSITE_EVENTS = {
    PROGRESS: 'progress',
    SAVE_FILE: 'saveFile',
    PARSE_RESOURCE: 'parseResource',
    COMPLETE: 'complete',
    VIDEO: 'video',
    DIALOGUES: 'dialogues',
    DIALOGUES_AUDIO: 'dialogues_audio',
    NARRATIONS: 'narrations',
    NARRATIONS_AUDIO: 'narrations_audio',
    CANCEL: 'cancel',
    UPLOAD_VIDEO: 'uploadVideo',
}
export const useCompsite = (_options?: any) => {
    const w = 720;
    const h = 1280;
    const cancelRef = ref<boolean>(false);
    const abortControllers: AbortController[] = []; // 保存所有 AbortController，用于取消网络请求
    const events = ref<any>({
        [COMPSITE_EVENTS.SAVE_FILE]: () => { }
    });
    const createFileWriter = async (): Promise<{ writable: WritableStream, fileHandle: FileSystemFileHandle }> => {
        events.value[COMPSITE_EVENTS.SAVE_FILE]?.();

        try {
            const handle: FileSystemFileHandle = await (window as any).showSaveFilePicker({
                suggestedName: _options.output || 'output.mp4',
                types: [
                    {
                        description: 'MP4 Video',
                        accept: { 'video/mp4': ['.mp4'] },
                    },
                ],
            });

            const writable: WritableStream = await handle.createWritable();
            return { writable, fileHandle: handle };
        } catch (err) {
            console.error('创建文件失败:', err);
            throw err;
        }
    };


    const Tracks: any = {
        video: [],
        dialogues: [],
        dialogues_audio: [],
        narrations: [],
        narrations_audio: [],
    };
    let composer: ClipExporter | null = null;
    let currentStream: WritableStream | null = null; // 保存当前的文件流，用于取消时关闭

    // 清理所有资源的辅助函数
    const cleanup = () => {
        // 取消所有网络请求
        abortControllers.forEach(controller => {
            try {
                controller.abort();
            } catch (error) {
                console.warn('取消网络请求时出错:', error);
            }
        });
        abortControllers.length = 0;

        // 清理 composer
        if (composer) {
            try {
                composer.destroy();
            } catch (error) {
                console.warn('销毁 composer 时出错:', error);
            }
            composer = null;
        }

        // 关闭文件流
        if (currentStream) {
            try {
                // 尝试获取 writer 并 abort
                const writer = currentStream.getWriter();
                if (writer) {
                    writer.abort().catch(() => { });
                    writer.releaseLock();
                }
            } catch (error) {
                // 如果无法获取 writer，尝试直接关闭
                try {
                    if (currentStream && typeof (currentStream as any).abort === 'function') {
                        (currentStream as any).abort();
                    }
                } catch (e) {
                    console.warn('关闭文件流时出错:', e);
                }
            }
            currentStream = null;
        }

        // 清空 Tracks
        Tracks.video = [];
        Tracks.dialogues = [];
        Tracks.dialogues_audio = [];
        Tracks.narrations = [];
        Tracks.narrations_audio = [];
    };
    // 替换原来的 uploadVideo 方法
    const uploadVideo = async (file: File, chunkSize = 1 * 1024 * 1024) => {
        const totalChunks = Math.ceil(file.size / chunkSize);

        try {
            await $http.post('/app/shortplay/api/drama/uploadChunkCheck', {
                drama_id: _options.drama_id,
                episode_id: _options.episode_id,
                fileName: _options.output || 'output.mp4',
            }).then((res: any) => {
                if (res.code != ResponseCode.SUCCESS) {
                    throw new Error(res.msg);
                }
            }).catch((err: any) => {
                console.error('分片上传检查出错:', err);
                throw err;
            });
            for (let index = 0; index < totalChunks; index++) {
                if (cancelRef.value) {
                    events.value[COMPSITE_EVENTS.CANCEL]?.();
                    return;
                }

                const start = index * chunkSize;
                const end = Math.min(file.size, start + chunkSize);
                const chunk = file.slice(start, end);

                const formData = new FormData();
                formData.append('drama_id', _options.drama_id);
                formData.append('episode_id', _options.episode_id);
                formData.append('chunkIndex', index.toString());
                formData.append('totalChunks', totalChunks.toString());
                formData.append('chunkData', chunk);

                await $http.post('/app/shortplay/api/drama/uploadChunk', formData, {
                    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
                        if (progressEvent.lengthComputable) {
                            const chunkPercent = (progressEvent.loaded / (progressEvent.total || 1)) * 100;
                            const totalPercent = ((index + chunkPercent / 100) / totalChunks) * 100;
                            events.value[COMPSITE_EVENTS.UPLOAD_VIDEO]?.(Math.round(totalPercent));
                        }
                    }
                }).catch(err => {
                    console.error('分片上传出错:', err);
                    throw err;
                });
            }

            // 所有分片上传完成，通知服务端合并
            await $http.post('/app/shortplay/api/drama/mergeChunks', {
                totalChunks,
                drama_id: _options.drama_id,
                episode_id: _options.episode_id,
            });

            events.value[COMPSITE_EVENTS.COMPLETE]?.(true);
        } catch (err) {
            console.error('上传失败:', err);
            if (!cancelRef.value) {
                events.value[COMPSITE_EVENTS.COMPLETE]?.(false);
            }
        }
    };

    const start = async (stream: WritableStream, fileHandle: FileSystemFileHandle, data: any) => {
        currentStream = stream;
        const len = data.length;
        let offsetUs = 0;
        events.value[COMPSITE_EVENTS.PARSE_RESOURCE]?.(0);
        try {
            for (let i = 0; i < len; i++) {
                if (cancelRef.value) {
                    events.value[COMPSITE_EVENTS.CANCEL]?.();
                    cleanup();
                    return;
                }
                const item = data[i];
                let temp: ClipOptions;
                // 主轨道素材：不设置 offsetUs，让系统自动按顺序追加
                if (item.use_material_type === 'video') {
                    const controller = new AbortController();
                    abortControllers.push(controller);
                    const response = await fetch(item.video, { signal: controller.signal });
                    if (cancelRef.value) {
                        cleanup();
                        return;
                    }
                    temp = {
                        type: 'video',
                        stream: response.body!,
                        // 主轨道不需要设置 offsetUs，会自动计算
                        offsetUs,
                        durationUs: item.duration * 1000,
                    };
                } else {
                    if (item.image) {
                        const controller = new AbortController();
                        abortControllers.push(controller);
                        const response = await fetch(item.image, { signal: controller.signal });
                        if (cancelRef.value) {
                            cleanup();
                            return;
                        }
                        temp = {
                            type: 'image',
                            stream: response.body!,
                            // 主轨道不需要设置 offsetUs，会自动计算
                            offsetUs,
                            durationUs: item.duration * 1000,
                        };
                    } else {
                        const offscreen = new OffscreenCanvas(w, h);
                        const offscreenCtx = offscreen.getContext('2d')!;
                        offscreenCtx.fillStyle = 'black';
                        offscreenCtx.fillRect(0, 0, w, h);
                        const bitmap = offscreen.transferToImageBitmap();
                        temp = {
                            type: 'image',
                            stream: bitmap,
                            // 主轨道不需要设置 offsetUs，会自动计算
                            offsetUs,
                            durationUs: item.duration * 1000,
                        };
                    }
                }
                Tracks.video.push(temp);

                // 收集对话字幕片段
                if (item.dialogues && item.dialogues.length > 0) {
                    for (const dialogue of item.dialogues) {
                        Tracks.dialogues.push({
                            text: dialogue.content,
                            startTimeUs: offsetUs + dialogue.start_time * 1000,
                            endTimeUs: offsetUs + dialogue.end_time * 1000,
                        });

                        if (dialogue.audio) {
                            const controller = new AbortController();
                            abortControllers.push(controller);
                            const response = await fetch(dialogue.audio, { signal: controller.signal });
                            if (cancelRef.value) {
                                cleanup();
                                return;
                            }
                            const audioTemp: ClipOptions = {
                                type: 'audio',
                                stream: response.body!,
                                trackId: 'dialogue_audio', // 对话音频轨道
                                offsetUs: offsetUs + dialogue.start_time * 1000,
                                // durationUs 不设置，使用音频的实际时长
                            };
                            Tracks.dialogues_audio.push(audioTemp);
                        }
                    }
                }

                // 收集旁白字幕片段
                if (item.narration) {
                    Tracks.narrations.push({
                        text: item.narration,
                        startTimeUs: offsetUs,
                        endTimeUs: offsetUs + item.duration * 1000,
                    });

                    if (item.narration_audio) {
                        const controller = new AbortController();
                        abortControllers.push(controller);
                        const response = await fetch(item.narration_audio, { signal: controller.signal });
                        if (cancelRef.value) {
                            cleanup();
                            return;
                        }
                        const audioTemp: ClipOptions = {
                            type: 'audio',
                            stream: response.body!,
                            trackId: 'narration_audio', // 旁白音频轨道
                            offsetUs: offsetUs,
                            // durationUs 不设置，使用音频的实际时长
                        };
                        Tracks.narrations_audio.push(audioTemp);
                    }
                }
                offsetUs += item.duration * 1000;
                events.value[COMPSITE_EVENTS.PARSE_RESOURCE]?.(i / len * 100);
            }
            events.value[COMPSITE_EVENTS.PARSE_RESOURCE]?.(100);
            events.value[COMPSITE_EVENTS.PROGRESS]?.(0);
            if (cancelRef.value) {
                events.value[COMPSITE_EVENTS.CANCEL]?.();
                cleanup();
                return;
            }
            try {
                composer = new ClipExporter(w, h);
                composer.setTracks(Tracks);
                composer.on(COMPSITE_EVENTS.VIDEO, events.value[COMPSITE_EVENTS.VIDEO]);
                composer.on(COMPSITE_EVENTS.DIALOGUES, events.value[COMPSITE_EVENTS.DIALOGUES]);
                composer.on(COMPSITE_EVENTS.DIALOGUES_AUDIO, events.value[COMPSITE_EVENTS.DIALOGUES_AUDIO]);
                composer.on(COMPSITE_EVENTS.NARRATIONS, events.value[COMPSITE_EVENTS.NARRATIONS]);
                composer.on(COMPSITE_EVENTS.NARRATIONS_AUDIO, events.value[COMPSITE_EVENTS.NARRATIONS_AUDIO]);
                await composer.initialization();
                if (cancelRef.value) {
                    cleanup();
                    return;
                }
                composer.OutputProgress((progress: number) => {
                    if (!cancelRef.value) {
                        events.value[COMPSITE_EVENTS.PROGRESS]?.(progress);
                    }
                });
                // 导出
                if (cancelRef.value) {
                    cleanup();
                    return;
                }
                await composer.export(stream);
                if (cancelRef.value) {
                    cleanup();
                    return;
                }
                // 释放
                composer.destroy();
                composer = null;
                currentStream = null;
                // 清理已完成的网络请求控制器
                abortControllers.length = 0;
                const file = await fileHandle.getFile();
                events.value[COMPSITE_EVENTS.UPLOAD_VIDEO]?.(0);
                uploadVideo(file);
            } catch (error) {
                // 如果是取消导致的错误，不触发 complete(false)
                if (!cancelRef.value) {
                    events.value[COMPSITE_EVENTS.COMPLETE]?.(false);
                }
                console.info(error);
                cleanup();
            }
        } catch (error) {
            // 如果是取消导致的错误，不触发 complete(false)
            if (!cancelRef.value) {
                events.value[COMPSITE_EVENTS.COMPLETE]?.(false);
            }
            console.info(error);
            cleanup();
        }
    }
    const synthesis = (data: any) => {
        // 重置取消标志
        cancelRef.value = false;
        // 清理之前的资源
        cleanup();
        createFileWriter().then(({ writable, fileHandle }) => {
            if (cancelRef.value) {
                events.value[COMPSITE_EVENTS.CANCEL]?.();
                cleanup();
                return;
            }
            events.value[COMPSITE_EVENTS.SAVE_FILE]?.(true);
            if (cancelRef.value) {
                events.value[COMPSITE_EVENTS.CANCEL]?.();
                cleanup();
                return;
            }
            start(writable, fileHandle, data);
        }).catch((err: any) => {
            // 如果是用户取消文件选择，不触发错误事件
            if (!cancelRef.value) {
                events.value[COMPSITE_EVENTS.SAVE_FILE]?.(false);
            }
            console.info(err);
            cleanup();
        });
    }
    const cancel = () => {
        cancelRef.value = true;
        if (composer) {
            composer.cancel();
        }
        // 清理所有资源
        cleanup();
        events.value[COMPSITE_EVENTS.CANCEL]?.();
    }
    const on = (event: typeof COMPSITE_EVENTS[keyof typeof COMPSITE_EVENTS], callback: (data: any) => void) => {
        events.value[event] = callback;
    }
    const off = (event: typeof COMPSITE_EVENTS[keyof typeof COMPSITE_EVENTS]) => {
        delete events.value[event];
    }
    return {
        on,
        off,
        synthesis,
        cancel,
        cancelRef
    }
}