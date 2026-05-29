/// <reference types="vite/client" />
interface ImportMateEnv {
    readonly VITE_APP_TITLE: string,
    readonly VITE_REQUEST_BASE_URL: string | undefined
}
interface ImportMate {
    readonly env: ImportMateEnv
}
export { };
declare global {

    interface ObjectInterface {
        [propName: string]: any
    }
    type StorageInterface = string | string[] | object | object[] | number | number[] | null | ObjectInterface | ObjectInterface[]
    type LanguageInterface = 'zh-CN' | 'en';

    interface WebConfigInterface {
        web_name?: string,
        web_logo?: string,
        web_icp?: string,
        web_mps?: string,
        web_mps_text?: string,
        web_title?: string,
        version_name?: string,
        version?: number,
        copyright?: string,
        [propName: string]: any
    }
    interface StateInterface {
        AsideState: boolean
        NotMenusAsideState: boolean
        language: LanguageInterface
        InputFocusState: boolean
    }
    interface LanguageListInterface {
        label: string,
        value: LanguageInterface
    }
    interface UserInfoInterface {
        nickname: string,
        token: string,
        [propName: string]: any
    }
    interface ModelInterface {
        creative_script: any
        creative_episode: any
        creative_scenes: any
        creative_storyboards: any
        drama_cover: any
        scene_image: any
        actor_image: any
        actor_three_view_image: any
        storyboard_image: any
        character_look_costume: any
        actor_costume: any
        actor_costume_three_view: any
        prop_image: any
        prop_three_view_image: any
        storyboard_video: any
        dialogue_voice: any
        storyboard_narration_voice: any
        storyboard_sfx_voice: any
        storyboard_music_voice: any
        creative_video: any
        [propName: string]: any
    }
    interface TrackResourceInterface {
        id: string;
        duration: number;
        narration: string;
        use_material_type: string;
        video: string;
        image: string;
        dialogue_audio: string[];
        narration_audio: string;
        sfx_audio: string;
        dialogues: any[];
    }
    interface TrackInterface {
        video: string[];
        video_audio: string[];
        dialogue_audio: string[];
        narration_audio: string[];
        sfx_audio: string[];
    }
    interface TimeTask {
        nextTime: number;     // 下一次触发时间（绝对时间）
        cancelled: boolean;
        run(now: number): void;
    }
}