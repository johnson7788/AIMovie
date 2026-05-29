import {
    Combinator,
    AudioClip,
    EmbedSubtitlesClip,
    ImgClip,
    MP4Clip,
    renderTxt2ImgBitmap,
    OffscreenSprite,
} from '@webav/av-cliper';

type ClipType = 'video' | 'audio' | 'image' | 'text';
/**
 * 将时间（微秒）转换为 SRT 时间格式 (HH:MM:SS,mmm)
 */
function formatSrtTime(us: number): string {
    const totalMs = Math.floor(us / 1000);
    const hours = Math.floor(totalMs / 3600000);
    const minutes = Math.floor((totalMs % 3600000) / 60000);
    const seconds = Math.floor((totalMs % 60000) / 1000);
    const milliseconds = totalMs % 1000;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')},${String(milliseconds).padStart(3, '0')}`;
}


/**
 * 将单个文本片段转换为 SRT 格式
 * @param text 文本内容
 * @param startTimeUs 开始时间（微秒）
 * @param endTimeUs 结束时间（微秒）
 * @param index 字幕序号（从1开始）
 * @returns SRT 格式的字符串
 */
export function textToSrt(
    text: string,
    startTimeUs: number,
    endTimeUs: number,
    index = 1,
): string {
    return `${index}\n${formatSrtTime(startTimeUs)} --> ${formatSrtTime(endTimeUs)}\n${text}\n\n`;
}

export interface SubtitleStyle {
    color?: string;
    textBgColor?: string | null;
    type?: 'srt';
    fontFamily?: string;
    fontSize?: number;
    letterSpacing?: string | null;
    bottomOffset?: number;
    strokeStyle?: string;
    lineWidth?: number | null;
    lineCap?: CanvasLineCap | null;
    lineJoin?: CanvasLineJoin | null;
    textShadow?: {
        offsetX: number;
        offsetY: number;
        blur: number;
        color: string;
    };
    videoWidth: number;
    videoHeight: number;
    fontWeight?: string | number;
    fontStyle?: 'normal' | 'italic';
}

export interface ClipOptions {
    type: ClipType;
    stream?: ReadableStream|ImageBitmap;
    text?: string;
    style?: string;
    // 字幕相关配置
    subtitleSrt?: string; // SRT 格式的字幕内容
    subtitleStyle?: SubtitleStyle; // 字幕样式配置
    durationUs?: number; // 可选，默认用素材本身长度
    trackId?: string | number; // 轨道ID，默认为 'main'（主轨道）
    offsetUs?: number; // 插入时间（微秒），非主轨道可以使用此参数指定插入时间
}

export class ClipExporter {
    private combinator: Combinator;
    private tracks: any;
    private width: number;
    private height: number;
    private durationUs: number = 0;
    private cancelRef: boolean = false;
    // 保存所有创建的资源，以便在取消时释放
    private clips: Array<MP4Clip | ImgClip | AudioClip | EmbedSubtitlesClip> = [];
    private sprites: OffscreenSprite[] = [];
    constructor(width = 1280, height = 720, bgColor = '#000') {
        this.width = width;
        this.height = height;
        this.combinator = new Combinator({
            width,
            height,
            bgColor,
        });
    }
    setTracks(tracks: any) {
        this.tracks = tracks;
        return this;
    }
    async initializationDialogues() {
        if (this.cancelRef) {
            return;
        }
        this.events['dialogues']?.(0);
        const dialogueSubtitles: any[] = [];
        const dialoguesLength = this.tracks.dialogues.length;
        for (let i = 0; i < dialoguesLength; i++) {
            if (this.cancelRef) {
                return;
            }
            const track = this.tracks.dialogues[i];
            dialogueSubtitles.push({
                text: track.text,
                start: track.startTimeUs,
                end: track.endTimeUs,
            });
        }
        if (this.cancelRef) {
            return;
        }
        const clip = new EmbedSubtitlesClip(dialogueSubtitles, {
            videoWidth: this.width,
            videoHeight: this.height,
            fontSize: 24,
            fontFamily: 'Noto Sans SC',
            strokeStyle: '#000',
            lineWidth: 2,
            lineJoin: 'round',
            lineCap: 'round',
            bottomOffset: 100,
        });
        this.clips.push(clip);
        const spr = new OffscreenSprite(clip);
        spr.time.offset = 0;
        spr.time.duration = this.durationUs;
        this.sprites.push(spr);
        if (this.cancelRef) {
            return;
        }
        await this.combinator.addSprite(spr);
        this.events['dialogues']?.(100);
    }
    private narrationStyle = `
    font-size: 20px; 
  font-weight:600;
    color: white;
    -webkit-text-stroke: 1px #000;
    writing-mode: vertical-lr;
  text-orientation: upright;
  white-space:wrap;
  padding:10px;`;
    async initializationNarrations() {
        if (this.cancelRef) {
            return;
        }
        this.events['narrations']?.(0);
        this.narrationStyle = `
        height:${this.height / 2}px;
        ${this.narrationStyle}`;
        const narrationsLength = this.tracks.narrations.length;
        for (let i = 0; i < narrationsLength; i++) {
            if (this.cancelRef) {
                return;
            }
            const track = this.tracks.narrations[i];
            const clip = new ImgClip(
                await renderTxt2ImgBitmap(
                    track.text,
                    this.narrationStyle,
                ),
            );
            this.clips.push(clip);
            await clip.ready;
            if (this.cancelRef) {
                return;
            }
            const spr = new OffscreenSprite(clip);
            spr.time.offset = track.startTimeUs;
            spr.time.duration = track.endTimeUs - track.startTimeUs;
            this.sprites.push(spr);
            if (this.cancelRef) {
                return;
            }
            await this.combinator.addSprite(spr);
            this.events['narrations']?.(i / narrationsLength * 100);
        }
        this.events['narrations']?.(100);
    }
    private events: any = {
        video: () => { },
        dialogues: () => { },
        dialogues_audio: () => { },
        narrations: () => { },
        narrations_audio: () => { },
    };
    on(event: keyof typeof this.events, callback: (data: any) => void) {
        this.events[event] = callback;
    }
    off(event: keyof typeof this.events) {
        delete this.events[event];
    }
    async initialization() {
        if (this.cancelRef) {
            return;
        }
        let spr: OffscreenSprite;
        let clip: MP4Clip | ImgClip | AudioClip;
        this.events['video']?.(0);
        const videoLength = this.tracks.video.length;
        for (let i = 0; i < videoLength; i++) {
            if (this.cancelRef) {
                return;
            }
            const track = this.tracks.video[i];
            if (track.type === 'video') {
                clip = new MP4Clip(track.stream);
                this.clips.push(clip);
                spr = new OffscreenSprite(clip);
                spr.time.offset = track.offsetUs;
                spr.time.duration = track.durationUs;
            } else {
                clip = new ImgClip(track.stream);
                this.clips.push(clip);
                spr = new OffscreenSprite(clip);
                spr.time.offset = track.offsetUs;
                spr.time.duration = track.durationUs;
            }
            this.sprites.push(spr);
            this.durationUs += track.durationUs;
            if (this.cancelRef) {
                return;
            }
            await this.combinator.addSprite(spr);
            this.events['video']?.(i / videoLength * 100);
        }
        if (this.cancelRef) {
            return;
        }
        this.events['dialogues_audio']?.(0);
        const dialoguesAudioLength = this.tracks.dialogues_audio.length;
        for (let i = 0; i < dialoguesAudioLength; i++) {
            if (this.cancelRef) {
                return;
            }
            const track = this.tracks.dialogues_audio[i];
            clip = new AudioClip(track.stream);
            this.clips.push(clip);
            await clip.ready;
            if (this.cancelRef) {
                return;
            }
            spr = new OffscreenSprite(clip);
            spr.time.offset = track.offsetUs;
            spr.time.duration = clip.meta.duration;
            this.sprites.push(spr);
            if (this.cancelRef) {
                return;
            }
            await this.combinator.addSprite(spr);
            this.events['dialogues_audio']?.(i / dialoguesAudioLength * 100);
        }
        if (this.cancelRef) {
            return;
        }
        this.events['narrations_audio']?.(0);
        const narrationsAudioLength = this.tracks.narrations_audio.length;
        for (let i = 0; i < narrationsAudioLength; i++) {
            if (this.cancelRef) {
                return;
            }
            const track = this.tracks.narrations_audio[i];
            clip = new AudioClip(track.stream);
            this.clips.push(clip);
            await clip.ready;
            if (this.cancelRef) {
                return;
            }
            spr = new OffscreenSprite(clip);
            spr.time.offset = track.offsetUs;
            spr.time.duration = clip.meta.duration;
            this.sprites.push(spr);
            if (this.cancelRef) {
                return;
            }
            await this.combinator.addSprite(spr);
            this.events['narrations_audio']?.(i / narrationsAudioLength * 100);
        }
        if (this.cancelRef) {
            return;
        }
        await this.initializationDialogues();
        if (this.cancelRef) {
            return;
        }
        await this.initializationNarrations();
        if (this.cancelRef) {
            return;
        }
    }
    OutputProgress(callback: (data: any) => void) {
        this.combinator.on('OutputProgress', (progress: number) => {
            callback(progress * 100);
        });
    }
    async export(writer: WritableStream) {
        if(this.cancelRef){
            return;
        }
        await this.combinator.output().pipeTo(writer);
    }

    destroy() {
        // 释放所有 clips
        this.clips.forEach(clip => {
            try {
                if (clip && typeof (clip as any).destroy === 'function') {
                    (clip as any).destroy();
                }
            } catch (error) {
                console.warn('销毁 clip 时出错:', error);
            }
        });
        this.clips = [];

        // 释放所有 sprites
        this.sprites.forEach(sprite => {
            try {
                if (sprite && typeof sprite.destroy === 'function') {
                    sprite.destroy();
                }
            } catch (error) {
                console.warn('销毁 sprite 时出错:', error);
            }
        });
        this.sprites = [];

        // 销毁 combinator
        if (this.combinator) {
            try {
                this.combinator.destroy();
            } catch (error) {
                console.warn('销毁 combinator 时出错:', error);
            }
        }
    }
    cancel() {
        this.cancelRef = true;
        // 取消时立即释放所有资源
        this.destroy();
    }
}
