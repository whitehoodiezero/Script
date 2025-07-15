(() => {
    const sources = new Set();

    // Mengumpulkan dari tag <video>
    document.querySelectorAll('video').forEach(video => {
        if (video.src) sources.add(video.src);
        video.querySelectorAll('source').forEach(source => {
            if (source.src) sources.add(source.src);
        });
    });

    // Mengumpulkan dari tag <embed> dan <object>
    document.querySelectorAll('embed, object').forEach(el => {
        const url = el.src || el.data;
        if (url) sources.add(url);
    });

    // Mengumpulkan dari tag <iframe>
    document.querySelectorAll('iframe').forEach(iframe => {
        if (iframe.src) sources.add(iframe.src);
    });

    // Mengumpulkan dari atribut data-*
    document.querySelectorAll('*[data-video-src], *[data-src]').forEach(el => {
        const videoSrc = el.dataset.videoSrc || el.dataset.src;
        if (videoSrc) sources.add(videoSrc);
    });

    // Mengumpulkan dari background video CSS
    document.querySelectorAll('*').forEach(el => {
        const bg = getComputedStyle(el).background;
        const match = bg.match(/url\(["']?(.*?)["']?\)/);
        if (match && /\.(mp4|webm|mov|ogg)$/i.test(match[1])) {
            sources.add(match[1]);
        }
    });

    // Menampilkan hasil
    if (sources.size === 0) {
        console.log('Tidak ditemukan sumber video');
        return;
    }

    console.log('Daftar Sumber Video:');
    sources.forEach(src => console.log(`- ${src}`));
})();