import { ImageDurationClip } from '@/common/av-cliper/ImageDurationClip';
import { MP4Clip, ImgClip } from '@webav/av-cliper';

interface WorkerMessage {
    type: 'init' | 'load' | 'play' | 'pause' | 'destroy' | 'stop' | 'switchClip' | 'resize';
    offscreen?: OffscreenCanvas;
    TrackResource?: TrackResourceInterface[];
    index?: number;
    time?: number; // 用于 seek
    size?: {
        width: number;
        height: number;
    };
}

let canvas: OffscreenCanvas;
let ctx: OffscreenCanvasRenderingContext2D;
let currentTrackResourceIndex = 0;
let currentTrackResource: TrackResourceInterface;
let TrackResource: TrackResourceInterface[] = [];
let Tracks: any[] = [];
let currentVideoClip: any;
let nextVideoClip: any;

let timer: number | null = null;
let playStartTime = 0;
let isPlaying = false;
let ticking = false;
let currentTimeMs = 0;   // 逻辑时间轴（关键）


/** 初始化 Worker */
const initData = (data: WorkerMessage) => {
    if (data.offscreen) {
        canvas = data.offscreen;
        ctx = canvas.getContext('2d')!;
    }
    TrackResource = data.TrackResource!;
    for (let i = 0; i < Tracks.length; i++) {
        Tracks[i]?.destroy?.();
    }
    Tracks = [];

};
const resize = (data: WorkerMessage) => {
    if (data.size) {
        canvas.width = data.size.width;
        canvas.height = data.size.height;
    }
    renderFirstFrame();
}

/** 停止视频 */
const stop = () => {
    isPlaying = false;
    ticking = false;
    currentTimeMs = 0;
    if (timer !== null) {
        clearTimeout(timer);
        timer = null;
    }
    postMessage({
        type: 'stop',
    });
};
const pause = () => {
    if (!isPlaying) return;
    stop(); // currentTimeMs 已经保存
};


/** 加载视频 clip */
const loadClip = async (index: number) => {
    if (Tracks[index]) {
        return Tracks[index];
    }
    if (!TrackResource[index]) return null;
    const find = TrackResource[index];
    if (find.use_material_type === 'video' && find.video) {
        const videoStream = (await fetch(find.video)).body!;
        const clip = new MP4Clip(videoStream);
        await clip.ready;
        const [videoClip] = await clip.splitTrack();
        Tracks[index] = videoClip;
    } else if (find.use_material_type === 'image' && find.image) {
        const imageStream = await (await fetch(find.image)).blob();
        const imgClip = new ImgClip(await createImageBitmap(imageStream));
        await imgClip.ready;
        const clip = new ImageDurationClip(imgClip, find.duration * 1000);
        Tracks[index] = clip;
    } else {
        const offscreen = new OffscreenCanvas(canvas.width, canvas.height);
        const offscreenCtx = offscreen.getContext('2d')!;
        offscreenCtx.fillStyle = 'black';
        offscreenCtx.fillRect(0, 0, canvas.width, canvas.height);
        const bitmap = offscreen.transferToImageBitmap();
        const imgClip = new ImgClip(bitmap);
        await imgClip.ready;
        const clip = new ImageDurationClip(imgClip, find.duration * 1000);
        Tracks[index] = clip;
    }
    return Tracks[index];
};
// 渲染首帧
const renderFirstFrame = async () => {
    if (currentVideoClip) {
        const { state, video } = await currentVideoClip.tick(0);
        if (video && state === 'success') {
            renderFrame(video);
        }
    }
}
const preloadNext = (index: number) => {
    if (!TrackResource[index]) return;

    loadClip(index).then((clip) => {
        nextVideoClip = clip;
    });
};
const switchToNextClip = async () => {
    currentTrackResourceIndex++;
    if (nextVideoClip) {
        currentVideoClip = nextVideoClip;
        nextVideoClip = null;
        postMessage({
            type: 'play',
            index: currentTrackResourceIndex,
        });
        currentTrackResource = TrackResource[currentTrackResourceIndex];
    } else {
        stop();
        return false;
    }

    // 预加载下下一个
    preloadNext(currentTrackResourceIndex + 1);
    return true;
};

/** 播放视频 */
const FPS = 60;
const FRAME_INTERVAL = Math.floor(1000 / FPS);
console.log('FPS', FPS, FRAME_INTERVAL + 'ms');
let currentTime = 0;
const renderFrame = async (video: any) => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const vw = video.displayWidth || video.codedWidth || video.width || canvas.width;
    const vh = video.displayHeight || video.codedHeight || video.height || canvas.height;

    const scale = Math.min(
        canvas.width / vw,
        canvas.height / vh
    );

    const drawWidth = Math.round(vw * scale);
    const drawHeight = Math.round(vh * scale);

    const x = Math.round((canvas.width - drawWidth) / 2);
    const y = Math.round((canvas.height - drawHeight) / 2);

    ctx.drawImage(video, x, y, drawWidth, drawHeight);
    const dialogue = currentTrackResource?.dialogues?.find((dialogue: any) => {
        return currentTime >= dialogue.start_time && currentTime <= dialogue.end_time;
    });
    const maxTextWidth = drawWidth - 20;
    if (dialogue) {
        /* 绘制字幕，如果字幕超出drawWidth，则换行 */
        ctx.fillStyle = 'white';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 2;
        // ctx.textBaseline = 'middle';
        fillText(dialogue.content, canvas.width / 2, drawHeight - 130, maxTextWidth);
    }
    if (currentTrackResource?.narration) {
        ctx.fillStyle = 'white';
        ctx.font = '16px Arial';
        ctx.textAlign = 'start';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 2;
        fillText(currentTrackResource.narration, x + 10, 30, maxTextWidth);
    }
    video.close();
}
const play = () => {
    if (isPlaying || ticking) return;
    ticking = true;
    isPlaying = true;
    playStartTime = performance.now() - currentTimeMs;
    postMessage({
        type: 'play',
        index: currentTrackResourceIndex,
    });
    currentTrackResource = TrackResource[currentTrackResourceIndex];
    const loop = async () => {
        if (!isPlaying) return;
        const now = performance.now();
        currentTimeMs = Math.round((now - playStartTime) * 1000);
        currentTime = currentTimeMs / 1000;
        const { state, video } = await currentVideoClip!.tick(currentTimeMs);
        // 广播当前播放时间
        postMessage({
            type: 'currentTime',
            currentTime: currentTime,
        });
        if (state === 'done') {
            if (await switchToNextClip()) {
                playStartTime = performance.now();
                currentTimeMs = 0;
                schedule();
            }
            return;
        }

        if (video && state === 'success') {
            renderFrame(video);
        }
        schedule();
    };

    const schedule = () => {
        timer = self.setTimeout(loop, FRAME_INTERVAL);
    };

    ticking = false;
    schedule();
};
const fillText = (text: string, x: number, y: number, maxTextWidth: number) => {
    const dialogueWidth = ctx.measureText(text).width;
    if (dialogueWidth > maxTextWidth) {
        const contentStrs = text.split('');
        let lines = [];
        let line = '';
        for (let i = 0; i < contentStrs.length; i++) {
            if (ctx.measureText(line + contentStrs[i]).width >= maxTextWidth) {
                lines.push(line);
                line = '';
            }
            line += contentStrs[i];
        }
        if (line != '') lines.push(line);
        for (let i = lines.length - 1; i >= 0; i--) {
            ctx.strokeText(lines[i], x, y + i * 24);
            ctx.fillText(lines[i], x, y + i * 24);
        }
    }
    else {
        ctx.strokeText(text, x, y);
        ctx.fillText(text, x, y);
    }
}

/** Worker 消息处理 */
onmessage = async (e: MessageEvent<WorkerMessage>) => {
    const data = e.data;
    switch (data.type) {
        case 'load':
            initData(data);
            currentTrackResourceIndex = data.index ?? 0;
            currentVideoClip = await loadClip(currentTrackResourceIndex);
            renderFirstFrame();
            preloadNext(currentTrackResourceIndex + 1);
            break;
        case 'resize':
            resize(data);
            break;
        case 'play':
            if (currentTrackResourceIndex !== data.index) {
                currentTrackResourceIndex = data.index ?? 0;
                currentVideoClip = await loadClip(currentTrackResourceIndex);
                renderFirstFrame();
                preloadNext(currentTrackResourceIndex + 1);
            }
            play();
            break;
        case 'switchClip':
            currentTrackResourceIndex = data.index ?? 0;
            currentVideoClip = await loadClip(currentTrackResourceIndex);
            renderFirstFrame();
            preloadNext(currentTrackResourceIndex + 1);
            break;
        case 'pause':
            pause();
            break;
        case 'stop':
            stop();
            break;
        case 'destroy':
            stop();
            currentVideoClip = null;
            nextVideoClip = null;
            break;
    }
};
