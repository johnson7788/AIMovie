export const useNotify = () => {
    const parseNotify = (notify: any) => {
        console.log(notify);
    }
    return {
        parse: parseNotify,
    }
}