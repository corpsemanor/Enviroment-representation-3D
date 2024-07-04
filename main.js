import * as THREE from './node_modules/three';
import { OrbitControls } from './node_modules/three/examples/jsm/controls/OrbitControls.js';
import { OBJExporter } from './node_modules/three/examples/jsm/exporters/OBJExporter.js';
import { saveAs } from './node_modules/file-saver';

let scene, camera, renderer, controls;

init();
loadData();

function init() {
    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 3, 10);

    renderer = new THREE.WebGLRenderer();
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.getElementById('container').appendChild(renderer.domElement);

    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(0, 10, 10).normalize();
    scene.add(light);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.25;
    controls.enableZoom = true;

    window.addEventListener('resize', onWindowResize, false);
    document.getElementById('exportButton').addEventListener('click', exportToOBJ);
    animate();
}

function loadData() {
    fetch('data/a.json')
        .then(response => response.json())
        .then(data => {
            buildObjects(data.embeds);
        })
        .catch(error => {
            console.error('Error loading data:', error);
        });
}

function buildObjects(embeds) {
    embeds.forEach(embed => {
        const { x, y, zLayer, rect } = embed;
        const { vertices, faces } = rect.data;

        const geometry = new THREE.BufferGeometry();
        const verticesArray = [];
        const indicesArray = [];

        for (let i = 0; i < vertices.length; i += 3) {
            verticesArray.push(vertices[i] + x, vertices[i + 1] + y, vertices[i + 2] + zLayer);
        }

        for (let i = 0; i < faces.length; i += 4) {
            indicesArray.push(faces[i], faces[i + 1], faces[i + 2]);
            indicesArray.push(faces[i], faces[i + 2], faces[i + 3]);
        }

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(verticesArray, 3));
        geometry.setIndex(indicesArray);

        const material = new THREE.MeshBasicMaterial({ color: 0x00ff00, wireframe: true });
        const mesh = new THREE.Mesh(geometry, material);
        
        scene.add(mesh);
    });
}

function exportToOBJ() {
    const exporter = new OBJExporter();
    const result = exporter.parse(scene);

    const blob = new Blob([result], { type: 'text/plain' });
    saveAs(blob, 'model.obj');
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