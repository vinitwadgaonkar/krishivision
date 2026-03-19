document.addEventListener('DOMContentLoaded', () => {

    // ═══ State ═══
    let geoState = { lat: null, lon: null, ready: false };
    let contextData = null;
    let soilFile = null, leafFile = null;

    // ═══ Elements ═══
    const $ = id => document.getElementById(id);
    const modeBtns = document.querySelectorAll('.mode-btn');
    const modePanels = document.querySelectorAll('.mode-panel');

    // ═══ Auto GPS on load ═══
    initGPS();

    // ═══ Mode Switching ═══
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            modePanels.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            $(`panel-${btn.dataset.mode}`).classList.add('active');
            $('results').style.display = 'none';
        });
    });

    // ═══ Soil Camera ═══
    $('btnSoilCamera').addEventListener('click', e => { e.stopPropagation(); $('soilInput').click(); });
    $('soilZone').addEventListener('click', e => {
        if (e.target.closest('.btn')) return;
        $('soilInput').click();
    });
    $('soilInput').addEventListener('change', e => {
        if (e.target.files[0]) { soilFile = e.target.files[0]; showPreview('soil'); }
    });
    $('btnSoilRetake').addEventListener('click', e => { e.stopPropagation(); resetPreview('soil'); });
    $('btnSoilAnalyze').addEventListener('click', e => { e.stopPropagation(); analyzeSoil(); });

    // ═══ Leaf Camera ═══
    $('btnLeafCamera').addEventListener('click', e => { e.stopPropagation(); $('leafInput').click(); });
    $('leafZone').addEventListener('click', e => {
        if (e.target.closest('.btn')) return;
        $('leafInput').click();
    });
    $('leafInput').addEventListener('change', e => {
        if (e.target.files[0]) { leafFile = e.target.files[0]; showPreview('leaf'); }
    });
    $('btnLeafRetake').addEventListener('click', e => { e.stopPropagation(); resetPreview('leaf'); });
    $('btnLeafAnalyze').addEventListener('click', e => { e.stopPropagation(); analyzeLeaf(); });

    // ═══ Manual Form ═══
    $('manualForm').addEventListener('submit', async e => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const data = {};
        for (const [k, v] of fd.entries()) { if (v !== '') data[k] = v; }
        if (Object.keys(data).length < 3) { toast('Enter at least 3 values', true); return; }

        if (geoState.ready) {
            if (!data.temperature && contextData?.weather?.temperature)
                data.temperature = contextData.weather.temperature;
            if (!data.humidity && contextData?.weather?.humidity)
                data.humidity = contextData.weather.humidity;
            if (!data.rainfall && contextData?.weather?.rainfall_3day)
                data.rainfall = contextData.weather.rainfall_3day;
        }

        showLoading('Analyzing soil data...', 'Running ML prediction');
        try {
            const res = await fetch('/api/analyze-manual', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
            });
            const result = await res.json();
            if (!res.ok) { toast(result.error, true); return; }
            renderSoilResults(result, false);
        } catch { toast('Network error', true); }
        finally { hideLoading(); }
    });

    $('btnBack').addEventListener('click', () => {
        $('results').style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // ═══ GPS + Auto Context ═══
    function initGPS() {
        if (!navigator.geolocation) {
            $('contextText').textContent = 'GPS unavailable';
            return;
        }
        $('contextText').textContent = 'Getting location...';
        navigator.geolocation.getCurrentPosition(
            async pos => {
                geoState.lat = pos.coords.latitude;
                geoState.lon = pos.coords.longitude;
                geoState.ready = true;
                $('contextBadge').classList.add('active');
                $('contextText').textContent = 'Location locked';
                await fetchContext();
            },
            () => { $('contextText').textContent = 'Location denied'; },
            { enableHighAccuracy: true, timeout: 15000 }
        );
    }

    async function fetchContext() {
        try {
            const res = await fetch(`/api/context?lat=${geoState.lat}&lon=${geoState.lon}`);
            contextData = await res.json();
            renderContextBar();
        } catch { /* silent fail */ }
    }

    function renderContextBar() {
        if (!contextData) return;
        const bar = $('contextBar');
        bar.style.display = 'block';
        // Reposition mode nav
        document.querySelector('.mode-nav').style.top = '96px';

        const w = contextData.weather || {};
        const s = contextData.season || {};
        const r = contextData.regional_soil || {};

        $('chipLocation').querySelector('span').textContent =
            w.location?.area ? `${w.location.area}, ${w.location.region}` : `${geoState.lat.toFixed(2)}, ${geoState.lon.toFixed(2)}`;
        $('chipWeather').querySelector('span').textContent =
            w.success ? `${w.temperature}°C, ${w.humidity}% RH` : '--';
        $('chipSeason').querySelector('span').textContent = s.season || '--';
        $('chipSoilType').querySelector('span').textContent = r.dominant_soil || '--';
    }

    // ═══ Preview ═══
    function showPreview(type) {
        const file = type === 'soil' ? soilFile : leafFile;
        const reader = new FileReader();
        reader.onload = e => {
            $(type + 'Img').src = e.target.result;
            $(type + 'Zone').style.display = 'none';
            $(type + 'Preview').style.display = 'block';
        };
        reader.readAsDataURL(file);
    }

    function resetPreview(type) {
        if (type === 'soil') { soilFile = null; $('soilInput').value = ''; }
        else { leafFile = null; $('leafInput').value = ''; }
        $(type + 'Zone').style.display = '';
        $(type + 'Preview').style.display = 'none';
    }

    // ═══ Soil Analysis ═══
    async function analyzeSoil() {
        if (!soilFile) return;
        const steps = ['Reading soil image', 'Analyzing color & texture', 'Fetching weather data', 'Running ML prediction', 'Generating recommendations'];
        showLoading('Scanning your soil...', 'AI vision + weather + ML', steps);

        const fd = new FormData();
        fd.append('image', soilFile);
        if (geoState.ready) {
            fd.append('lat', geoState.lat);
            fd.append('lon', geoState.lon);
        }
        try {
            animateSteps(steps);
            const res = await fetch('/api/scan-soil', { method: 'POST', body: fd });
            const data = await res.json();
            if (!res.ok) { toast(data.error, true); return; }
            renderSoilResults(data, true);
        } catch { toast('Network error', true); }
        finally { hideLoading(); }
    }

    // ═══ Leaf Analysis ═══
    async function analyzeLeaf() {
        if (!leafFile) return;
        const steps = ['Processing leaf image', 'Segmenting leaf area', 'Analyzing colors', 'Detecting deficiencies', 'Checking for diseases'];
        showLoading('Diagnosing your crop...', 'Leaf color + pattern analysis', steps);

        const fd = new FormData();
        fd.append('image', leafFile);
        if (geoState.ready) {
            fd.append('lat', geoState.lat);
            fd.append('lon', geoState.lon);
        }
        try {
            animateSteps(steps);
            const res = await fetch('/api/scan-leaf', { method: 'POST', body: fd });
            const data = await res.json();
            if (!res.ok) { toast(data.error, true); return; }
            renderLeafResults(data);
        } catch { toast('Network error', true); }
        finally { hideLoading(); }
    }

    // ═══ Render Soil Results ═══
    function renderSoilResults(data, showVision) {
        $('results').style.display = 'block';

        // Vision card
        const vc = $('soilVisionCard');
        if (showVision && data.soil_analysis) {
            vc.style.display = '';
            const sa = data.soil_analysis;
            $('vSoilType').textContent = sa.soil_type?.type || '--';
            $('vSoilConf').textContent = sa.soil_type?.confidence ? `${(sa.soil_type.confidence * 100).toFixed(0)}% confidence` : '';
            $('vMoisture').textContent = sa.moisture ? `${sa.moisture.level} (${sa.moisture.estimated_percent}%)` : '--';
            $('vOC').textContent = sa.organic_carbon ? `${sa.organic_carbon.estimated_percent}% (${sa.organic_carbon.level})` : '--';
            $('vTexture').textContent = sa.texture?.type || '--';
            $('vPH').textContent = sa.ph_estimate ? `~${sa.ph_estimate.value} (${sa.ph_estimate.range})` : '--';
            $('vColor').textContent = sa.color?.description || '--';
            const swatch = $('vColorSwatch');
            swatch.style.background = sa.color?.dominant_hex || '#888';
        } else { vc.style.display = 'none'; }

        // Leaf cards off
        $('leafDoctorCard').style.display = 'none';
        $('leafRecsCard').style.display = 'none';

        // SQI
        if (data.soil_health) {
            $('sqiCard').style.display = '';
            const sqi = data.soil_health.sqi || 0;
            const rating = data.soil_health.rating || 'Unknown';
            animateGauge(sqi);
            $('sqiNum').textContent = sqi.toFixed(2);
            const badge = $('sqiBadge');
            badge.textContent = rating;
            badge.className = 'sqi-badge ' + rating.toLowerCase();
        }

        // Nutrients
        if (data.nutrient_status && Object.keys(data.nutrient_status).length) {
            $('nutrientCard').style.display = '';
            renderNutrients(data.nutrient_status);
        } else { $('nutrientCard').style.display = 'none'; }

        // Crops
        if (data.crop_recommendations?.length) {
            $('cropCard').style.display = '';
            renderCrops(data.crop_recommendations);
        } else { $('cropCard').style.display = 'none'; }

        // Fertilizer
        if (data.fertilizer_recommendations) {
            $('fertCard').style.display = '';
            renderFertilizer(data.fertilizer_recommendations);
        } else { $('fertCard').style.display = 'none'; }

        setTimeout(() => $('results').scrollIntoView({ behavior: 'smooth' }), 150);
    }

    // ═══ Render Leaf Results ═══
    function renderLeafResults(data) {
        $('results').style.display = 'block';
        $('soilVisionCard').style.display = 'none';
        $('sqiCard').style.display = 'none';
        $('nutrientCard').style.display = 'none';
        $('cropCard').style.display = 'none';
        $('fertCard').style.display = 'none';

        const la = data.leaf_analysis;

        // Health ring
        $('leafDoctorCard').style.display = '';
        const score = la.health_score || 0;
        $('healthScore').textContent = (score * 100).toFixed(0) + '%';
        const arc = $('healthArc');
        const circumference = 2 * Math.PI * 52;
        animateArc(arc, score * circumference, circumference);

        const hs = $('healthStatus');
        hs.textContent = la.overall_status || '--';
        hs.className = 'health-status ' + (score > 0.7 ? 'healthy' : score > 0.4 ? 'moderate' : 'severe');

        // Deficiencies
        const dl = $('deficiencyList');
        dl.innerHTML = '';
        if (la.deficiencies?.length) {
            dl.innerHTML = '<h4 style="font-size:.8rem;color:var(--g600);margin:.75rem 0 .4rem">Nutrient Deficiencies Detected</h4>';
            la.deficiencies.forEach(d => {
                const badgeClass = d.severity === 'Severe' ? 'badge-severe' : d.severity === 'Moderate' ? 'badge-moderate' : 'badge-mild';
                dl.innerHTML += `<div class="issue-item">
                    <div class="issue-icon def">${d.nutrient[0]}</div>
                    <div class="issue-info">
                        <div class="issue-name">${d.nutrient} Deficiency <span class="issue-badge ${badgeClass}">${d.severity}</span></div>
                        <div class="issue-detail">${d.symptoms}</div>
                        <div class="issue-treatment">${d.treatment}</div>
                    </div>
                </div>`;
            });
        }

        // Diseases
        const disl = $('diseaseList');
        disl.innerHTML = '';
        if (la.diseases?.length) {
            disl.innerHTML = '<h4 style="font-size:.8rem;color:var(--g600);margin:.75rem 0 .4rem">Possible Diseases</h4>';
            la.diseases.forEach(d => {
                disl.innerHTML += `<div class="issue-item">
                    <div class="issue-icon dis">!</div>
                    <div class="issue-info">
                        <div class="issue-name">${d.disease} <span class="issue-badge badge-moderate">${(d.confidence * 100).toFixed(0)}%</span></div>
                        <div class="issue-detail">${d.description}</div>
                        <div class="issue-treatment">${d.treatment}</div>
                    </div>
                </div>`;
            });
        }

        // Leaf recommendations / treatment plan
        if (la.recommendations?.length) {
            $('leafRecsCard').style.display = '';
            const lr = $('leafRecs');
            lr.innerHTML = '';
            la.recommendations.forEach(r => {
                if (r.type === 'info') {
                    lr.innerHTML += `<p style="color:var(--emerald-600);font-weight:600">${r.message}</p>`;
                } else if (r.type === 'deficiency') {
                    const sevClass = r.severity === 'Severe' ? 'badge-severe' : r.severity === 'Moderate' ? 'badge-moderate' : 'badge-mild';
                    lr.innerHTML += `<div class="issue-item">
                        <div class="issue-icon def">${r.nutrient[0]}</div>
                        <div class="issue-info">
                            <div class="issue-name">${r.nutrient} <span class="issue-badge ${sevClass}">${r.severity}</span></div>
                            <div class="issue-treatment">${r.action}</div>
                        </div>
                    </div>`;
                } else if (r.type === 'disease') {
                    lr.innerHTML += `<div class="issue-item">
                        <div class="issue-icon dis">!</div>
                        <div class="issue-info">
                            <div class="issue-name">${r.disease}</div>
                            <div class="issue-treatment">${r.action}</div>
                        </div>
                    </div>`;
                }
            });
        } else { $('leafRecsCard').style.display = 'none'; }

        setTimeout(() => $('results').scrollIntoView({ behavior: 'smooth' }), 150);
    }

    // ═══ Shared Renderers ═══
    const NUTRIENT_NAMES = {pH:'pH',EC:'EC',OC:'Org.Carbon',N:'Nitrogen',P:'Phosphorus',K:'Potassium',S:'Sulphur',Zn:'Zinc',B:'Boron',Fe:'Iron',Cu:'Copper',Mn:'Manganese'};

    function renderNutrients(ns) {
        const grid = $('nutrientGrid');
        grid.innerHTML = '';
        for (const [k, info] of Object.entries(ns)) {
            const sc = 's-' + info.status.toLowerCase().replace(/[\s()]/g, '-');
            grid.innerHTML += `<div class="nut-item"><div class="nut-name">${NUTRIENT_NAMES[k]||k}</div><div class="nut-val">${typeof info.value==='number'?info.value.toFixed(2):info.value}</div><div class="nut-unit">${info.unit}</div><span class="nut-status ${sc}">${info.status}</span></div>`;
        }
    }

    function renderCrops(crops) {
        const cl = $('cropList');
        cl.innerHTML = '';
        crops.forEach((c, i) => {
            cl.innerHTML += `<div class="crop-item"><span class="crop-rank">${i+1}</span><span class="crop-name">${c.crop}</span><span class="crop-conf">${(c.confidence*100).toFixed(1)}%</span></div>`;
        });
    }

    function renderFertilizer(f) {
        const fc = $('fertContent');
        fc.innerHTML = '';
        if (f.deficiencies?.length) fc.innerHTML += `<div class="fert-section"><div class="fert-title"><span class="dot dot-r"></span>Deficiencies</div><ul class="fert-list">${f.deficiencies.map(d=>`<li>${d}</li>`).join('')}</ul></div>`;
        if (f.fertilizers?.length) fc.innerHTML += `<div class="fert-section"><div class="fert-title"><span class="dot dot-g"></span>Fertilizers</div><ul class="fert-list">${f.fertilizers.map(d=>`<li>${d}</li>`).join('')}</ul></div>`;
        if (f.amendments?.length) fc.innerHTML += `<div class="fert-section"><div class="fert-title"><span class="dot dot-a"></span>Amendments</div><ul class="fert-list">${f.amendments.map(d=>`<li>${d}</li>`).join('')}</ul></div>`;
    }

    // ═══ Animations ═══
    function animateGauge(sqi) {
        const max = 251.2;
        const arc = $('gaugeArc');
        const needle = $('gaugeNeedle');
        const dur = 1200;
        const start = performance.now();
        (function frame(now) {
            const p = Math.min((now - start) / dur, 1);
            const e = 1 - Math.pow(1 - p, 3);
            arc.setAttribute('stroke-dasharray', `${e * sqi * max} ${max}`);
            needle.setAttribute('transform', `rotate(${-90 + e * sqi * 180}, 100, 100)`);
            if (p < 1) requestAnimationFrame(frame);
        })(performance.now());
    }

    function animateArc(el, target, circum) {
        const dur = 1000;
        const start = performance.now();
        (function frame(now) {
            const p = Math.min((now - start) / dur, 1);
            const e = 1 - Math.pow(1 - p, 3);
            el.setAttribute('stroke-dasharray', `${e * target} ${circum}`);
            if (p < 1) requestAnimationFrame(frame);
        })(performance.now());
    }

    function animateSteps(steps) {
        const container = $('loaderSteps');
        container.innerHTML = steps.map(s => `<div class="step"><span class="step-check">○</span>${s}</div>`).join('');
        const els = container.querySelectorAll('.step');
        steps.forEach((_, i) => {
            setTimeout(() => {
                if (els[i]) { els[i].classList.add('done'); els[i].querySelector('.step-check').textContent = '✓'; }
            }, (i + 1) * 600);
        });
    }

    // ═══ Utilities ═══
    function showLoading(title, sub, steps) {
        $('loaderTitle').textContent = title;
        $('loaderSub').textContent = sub;
        $('loaderSteps').innerHTML = '';
        $('loading').style.display = 'flex';
    }
    function hideLoading() { $('loading').style.display = 'none'; }

    function toast(msg, err) {
        document.querySelectorAll('.toast').forEach(t => t.remove());
        const t = document.createElement('div');
        t.className = 'toast' + (err ? ' err' : '');
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 4000);
    }
});
