let scene, camera, renderer, controls;

init();
loadData();

function init() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xa0a0a0);

    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 3, 10);

    renderer = new THREE.WebGLRenderer();
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.getElementById('container').appendChild(renderer.domElement);

    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(0, 10, 10).normalize();
    scene.add(light);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.25;
    controls.enableZoom = true;

    window.addEventListener('resize', onWindowResize, false);
    animate();
}

function loadData() {
    fetch('data/a.json')
        .then(response => response.json())
        .then(data => {
            console.log('Loaded data:', data); // Добавлено для отладки
            buildWalls(data.walls);
            buildDoors(data.doors);
            buildWindows(data.windows);
        })
        .catch(error => console.error('Error loading data:', error));
}

function buildWalls(walls) {
    const defaultWallHeight = 3;  // Высота по умолчанию
    const wallMaterial = new THREE.MeshBasicMaterial({ color: 0xff0000 });

    walls.forEach(wall => {
        const length = parseFloat(wall.lengthFormatted.replace('m', ''));
        const height = wall.height !== null ? wall.height : defaultWallHeight;
        const thickness = wall.thickness !== null ? wall.thickness / 100 : 0.1;

        if (isNaN(length) || isNaN(height) || isNaN(thickness)) {
            console.error('Invalid wall dimensions:', wall);
            return;
        }

        const geometry = new THREE.BoxGeometry(length, height, thickness);

        const mesh = new THREE.Mesh(geometry, wallMaterial);
        mesh.position.set(wall.x, height / 2, wall.y);
        scene.add(mesh);
        console.log('Added wall mesh:', mesh); // Отладка мешей
    });
}

function buildDoors(doors) {
    const doorHeight = 2.1;
    const doorWidth = 0.9;
    const doorMaterial = new THREE.MeshBasicMaterial({ color: 0x00ff00 });

    doors.forEach(door => {
        const thickness = door.thickness !== null ? door.thickness / 100 : 0.1;

        if (isNaN(door.x) || isNaN(door.y) || isNaN(thickness)) {
            console.error('Invalid door dimensions:', door);
            return;
        }

        const geometry = new THREE.BoxGeometry(doorWidth, doorHeight, thickness);

        const mesh = new THREE.Mesh(geometry, doorMaterial);
        mesh.position.set(door.x, doorHeight / 2, door.y);
        scene.add(mesh);
        console.log('Added door mesh:', mesh); // Отладка мешей
    });
}

function buildWindows(windows) {
    const windowHeight = 1.5;
    const windowWidth = 1;
    const windowMaterial = new THREE.MeshBasicMaterial({ color: 0x0000ff });

    windows.forEach(window => {
        const thickness = window.thickness !== null ? window.thickness / 100 : 0.1;

        if (isNaN(window.x) || isNaN(window.y) || isNaN(thickness)) {
            console.error('Invalid window dimensions:', window);
            return;
        }

        const geometry = new THREE.BoxGeometry(windowWidth, windowHeight, thickness);

        const mesh = new THREE.Mesh(geometry, windowMaterial);
        mesh.position.set(window.x, windowHeight / 2, window.y);
        scene.add(mesh);
        console.log('Added window mesh:', mesh); // Отладка мешей
    });
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}
