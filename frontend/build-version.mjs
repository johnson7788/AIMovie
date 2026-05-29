import fs from 'fs';

// 读取 package.json 文件
const packageJsonPath = './package.json';
const packageJsonContent = fs.readFileSync(packageJsonPath, 'utf8');
const packageJson = JSON.parse(packageJsonContent);

// 递增版本号
const versionParts = packageJson.version.split('.');
versionParts[2] = (parseInt(versionParts[2], 10) + 1).toString();
if (versionParts[2] > 99) {
    versionParts[2] = '0';
    versionParts[1] = (parseInt(versionParts[1], 10) + 1).toString();
}
const newVersion = versionParts.join('.');

// 更新 package.json 中的版本号
packageJson.version = newVersion;

// 写入 package.json 文件
fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2));
fs.writeFileSync('./public/aimovie/static/version.json', JSON.stringify({ version: newVersion }, null, 2));


const indexHtml = fs.readFileSync('./index.html', 'utf8');
// 查找meta标签name=version,修改content=版本号
const newHtml = indexHtml.replace(/<meta name="version" content=".*">/, '<meta name="version" content="' + newVersion + '">');
fs.writeFileSync('./index.html', newHtml);
console.log(`Version updated to: ${newVersion}`);
