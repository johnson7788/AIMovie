import { onWindowResize } from "@/common/functions";

export const useAVCanvas = (cvsWrapEl: Ref<HTMLCanvasElement>, cvsWrapElWrapper: Ref<HTMLDivElement>) => {
    let offscreen: OffscreenCanvas | undefined;
    const isPlaying = ref(false);
    let currentTrackResourceIndex: number = 0;
    // 播放进度事件回调
    const currentTimeEvents: ((currentTime: number) => void)[] = [];
    const onCurrentTime = (callback: (currentTime: number) => void) => {
        currentTimeEvents.push(callback);
    }
    const offCurrentTime = (callback: (currentTime: number) => void) => {
        currentTimeEvents.splice(currentTimeEvents.indexOf(callback), 1);
    }
    // 切换素材事件
    const switchToNextClipEvents: ((currentTrackResource: TrackResourceInterface) => void)[] = [];
    const onSwitchToNextClip = (callback: (currentTrackResource: TrackResourceInterface) => void) => {
        switchToNextClipEvents.push(callback);
    }
    const offSwitchToNextClip = (callback: (currentTrackResource: TrackResourceInterface) => void) => {
        switchToNextClipEvents.splice(switchToNextClipEvents.indexOf(callback), 1);
    }
    const worker = new Worker(new URL('@/workers/loadStream.ts', import.meta.url), { type: 'module' });
    worker.onmessage = (e) => {
        const data = e.data;
        switch (data.type) {
            case 'stop':
                isPlaying.value = false;
                break;
            case 'play':
                currentTrackResourceIndex = data.index;
                isPlaying.value = true;
                const currentTrackResource = TrackResource[currentTrackResourceIndex];
                initAudio(currentTrackResource);
                switchToNextClipEvents.forEach((callback) => callback(currentTrackResource));
                break;
            case 'currentTime':
                currentTimeEvents.forEach((callback) => callback(data.currentTime || 0));
                break;
        }
    }
    worker.onerror = (e) => {
        console.log('worker error', e);
    }
    const audioEls: HTMLAudioElement[] = [];
    const initAudio = (currentTrackResource: TrackResourceInterface) => {
        const dialogueAudio = currentTrackResource.dialogue_audio;
        const loopAudio = (index: number = 0) => {
            const dialogue = dialogueAudio[index];
            if (dialogue) {
                const audio = new Audio();
                audio.src = dialogue;
                audio.play();
                const audioElIndex = audioEls.push(audio);
                audio.addEventListener('ended', () => {
                    index++;
                    audioEls.splice(audioElIndex - 1, 1);
                    if (isPlaying.value) {
                        loopAudio(index);
                    }
                });
            }
        }
        loopAudio(0);
        const narrationAudio = currentTrackResource.narration_audio;
        if (narrationAudio) {
            const audio = new Audio();
            audio.src = narrationAudio;
            audio.play();
            const audioElIndex = audioEls.push(audio);
            audio.addEventListener('ended', () => {
                audioEls.splice(audioElIndex - 1, 1);
            });
        }
        const sfxAudio = currentTrackResource.sfx_audio;
        if (sfxAudio) {
            const audio = new Audio();
            audio.src = sfxAudio;
            audio.play();
            const audioElIndex = audioEls.push(audio);
            audio.addEventListener('ended', () => {
                audioEls.splice(audioElIndex - 1, 1);
            });
        }
    }
    /**
     * 轨道资源
     * video: 视频资源
     * dialogue_audio: 对话音频资源
     * narration_audio: 旁白音频资源
     * sfx_audio: 音效音频资源
     */
    let TrackResource: TrackResourceInterface[] = [];
    /**
     * 解析轨道资源
     * @param currentStoryboard 当前片段
     * @param storyboards 所有片段
     * @returns 
     */
    const parseTrackResource = async (storyboards: any[], currentStoryboard?: any) => {
        if (currentStoryboard) {
            currentTrackResourceIndex = storyboards.findIndex((item: any) => item.id === currentStoryboard.id) || 0;
        }
        TrackResource = [];
        const storyboardsLen = storyboards.length;
        for (let i = 0; i < storyboardsLen; i++) {
            const storyboard = storyboards[i];
            const resource: TrackResourceInterface = {
                id: storyboard.id,
                video: storyboard.video,
                image: storyboard.image,
                use_material_type: storyboard.use_material_type,
                duration: storyboard.duration,
                dialogue_audio: [],
                narration: storyboard.narration,
                narration_audio: storyboard.narration_audio,
                sfx_audio: storyboard.sfx_audio,
                dialogues: [],
            };
            if (storyboard.dialogues) {
                for (const dialogue of storyboard.dialogues) {
                    resource.dialogue_audio.push(dialogue.audio);
                    resource.dialogues.push({
                        start_time: dialogue.start_time,
                        end_time: dialogue.end_time,
                        content: dialogue.actor.name + ':' + dialogue.content,
                    });
                }
            }
            TrackResource.push(resource);
        }
        if (offscreen) {
            worker.postMessage({
                type: 'load',
                TrackResource,
                index: currentTrackResourceIndex,
            });
        } else {
            offscreen = cvsWrapEl.value.transferControlToOffscreen();
            offscreen.width = cvsWrapElWrapper.value.clientWidth;
            offscreen.height = cvsWrapElWrapper.value.clientHeight;
            worker.postMessage({
                type: 'load',
                offscreen,
                TrackResource,
                index: currentTrackResourceIndex,
            }, [offscreen]);
        }
    }
    const resize = () => {
        worker.postMessage({
            type: 'resize',
            size: {
                width: cvsWrapElWrapper.value.clientWidth,
                height: cvsWrapElWrapper.value.clientHeight,
            },
        });
    }
    onWindowResize(resize, 300);
    const play = (currentStoryboard?: any) => {
        if (currentStoryboard) {
            const find = TrackResource.findIndex((item: TrackResourceInterface) => item.id === currentStoryboard.id);
            if (find !== -1) {
                currentTrackResourceIndex = find;
            }
        }
        worker.postMessage({
            type: 'play',
            index: currentTrackResourceIndex,
        });
        isPlaying.value = true;
    }
    const pause = () => {
        isPlaying.value = false;
        worker.postMessage({
            type: 'pause',
        });
        audioEls.forEach((audio) => {
            audio.pause();
        });
        audioEls.splice(0, audioEls.length);
    }
    const seek = (time: number) => {
        worker.postMessage({
            type: 'seek',
            time,
        });
    }
    const stop = () => {
        worker.postMessage({
            type: 'stop',
        });
        isPlaying.value = false;
        audioEls.forEach((audio) => {
            audio.pause();
        });
        audioEls.splice(0, audioEls.length);
    }
    const destroy = () => {
        stop();
        worker.terminate();
        offscreen = undefined;
    }
    const switchClip = (currentStoryboard: any) => {
        const find = TrackResource.findIndex((item: TrackResourceInterface) => item.id === currentStoryboard.id);
        if (find !== -1) {
            currentTrackResourceIndex = find;
        }
        worker.postMessage({
            type: 'switchClip',
            index: currentTrackResourceIndex,
        });
    }
    return {
        isPlaying,
        play,
        pause,
        stop,
        parseTrackResource,
        destroy,
        seek,
        onCurrentTime,
        offCurrentTime,
        onSwitchToNextClip,
        offSwitchToNextClip,
        switchClip,
    };
}