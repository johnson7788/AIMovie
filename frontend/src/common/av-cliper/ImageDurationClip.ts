import type { IClip } from '@webav/av-cliper';
import { ImgClip } from '@webav/av-cliper';

export class ImageDurationClip implements IClip {
    private img: ImgClip;
    private durationMs: number;

    ready: IClip['ready'];

    constructor(img: ImgClip, durationMs: number) {
        this.img = img;
        this.durationMs = durationMs;
        this.ready = img.ready;
    }

    get meta() {
        const meta = this.img.meta;
        return {
            width: meta.width,
            height: meta.height,
            displayWidth: meta.width,
            codedWidth: meta.width,
            displayHeight: meta.height,
            codedHeight: meta.height,
            duration: this.durationMs,
        };
    }

    async tick(time: number): Promise<Awaited<ReturnType<IClip['tick']>>> {
        if (time >= this.durationMs) {
            return {
                state: 'done',
            };
        }

        const ret = await this.img.tick(time);
        return {
            ...ret,
            state: 'success',
        };
    }

    async split(time: number): Promise<[this, this]> {
        if (time <= 0 || time >= this.durationMs) {
            throw new Error('split time out of range');
        }

        const left = new ImageDurationClip(
            await this.img.clone(),
            time,
        ) as this;

        const right = new ImageDurationClip(
            await this.img.clone(),
            this.durationMs - time,
        ) as this;

        return [left, right];
    }

    async clone(): Promise<this> {
        return new ImageDurationClip(
            await this.img.clone(),
            this.durationMs,
        ) as this;
    }

    destroy() {
        this.img.destroy();
    }
}
