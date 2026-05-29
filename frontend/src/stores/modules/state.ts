import { useStorage } from '@/composables/useStorage';
type StateValueType<T extends keyof StateInterface> = StateInterface[T];
export default () => {
    const storage = useStorage();
    const LANGUARE: LanguageListInterface[] = [
        {
            label: '简体中文',
            value: 'zh-CN'
        },
        {
            label: 'English',
            value: 'en'
        }
    ];
    const STATE = ref<StateInterface>({
        AsideState: true,
        NotMenusAsideState: false,
        language: LANGUARE[0].value,
        InputFocusState: false
    });
    watch(() => STATE.value, (data) => {
        storage.set('STATE', data);
    },{
        deep: true
    })
    const initState = () => {
        const data = storage.get('STATE') as StateInterface;
        if (data) {
            if(!data.language){
                data.language=LANGUARE[0].value;
            }
            if(data.InputFocusState === undefined){
                data.InputFocusState = false;
            }
            STATE.value = data;
        }
    }
    const toggle = <T extends keyof StateInterface>(key: T) => {
        STATE.value[key] = !STATE.value[key] as StateValueType<T>;
    }
    const setState = <T extends keyof StateInterface>(key: T, value: StateValueType<T>) => {
        STATE.value[key] = value;
    }

    return {
        STATE,
        LANGUARE,
        initState,
        setState,
        toggle
    };
}