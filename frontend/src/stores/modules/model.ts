import { useStorage } from '@/composables/useStorage';
export default () => {
    const storage = useStorage();
    const MODEL = ref<ModelInterface>({
        creative_script: [],
        creative_episode: [],
        creative_scenes: [],
        creative_storyboards: [],
        drama_cover: [],
        scene_image: [],
        actor_image: [],
        actor_three_view_image: [],
        storyboard_image: [],
        character_look_costume: [],
        actor_costume: [],
        actor_costume_three_view: [],
        prop_image: [],
        prop_three_view_image: [],
        storyboard_video: [],
        dialogue_voice: [],
        storyboard_narration_voice: [],
        storyboard_sfx_voice: [],
        storyboard_music_voice: [],
        creative_video: [],
    });
    watch(() => MODEL.value, (data) => {
        storage.set('MODEL', data, 10 * 60);
    }, {
        deep: true
    })
    const initModel = () => {
        const data = storage.get('MODEL') as ModelInterface;
        if (data) {
            MODEL.value = data;
        }
    }
    const setModel = (model: ModelInterface) => {
        MODEL.value = model;
    }
    const getModel = (scene: keyof ModelInterface,model_id?: any) => {
        if(model_id){
            return MODEL.value[scene].find((item: any) => item.id === model_id);
        }
        return MODEL.value[scene] || [];
    }

    return {
        MODEL,
        initModel,
        setModel,
        get: getModel
    };
}