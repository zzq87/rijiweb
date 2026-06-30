(function() {
    'use strict';

    var toggle = document.getElementById('navToggle');
    var menu = document.getElementById('navMenu');

    if (toggle && menu) {
        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            menu.classList.toggle('open');
            if (menu.classList.contains('open')) {
                toggle.innerHTML = '&#10005;';
            } else {
                toggle.innerHTML = '&#9776;';
            }
        });

        document.addEventListener('click', function(e) {
            if (menu.classList.contains('open') &&
                !toggle.contains(e.target) &&
                !menu.contains(e.target)) {
                menu.classList.remove('open');
                toggle.innerHTML = '&#9776;';
            }
        });

        menu.querySelectorAll('a').forEach(function(link) {
            link.addEventListener('click', function() {
                menu.classList.remove('open');
                toggle.innerHTML = '&#9776;';
            });
        });
    }

    var flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(function(msg) {
        setTimeout(function() {
            msg.style.transition = 'opacity 0.3s ease';
            msg.style.opacity = '0';
            setTimeout(function() {
                if (msg.parentNode) {
                    msg.parentNode.removeChild(msg);
                }
            }, 300);
        }, 4000);
    });

    var idleTime = 0;
    var idleMax = 28 * 60 * 1000;

    function resetIdle() {
        idleTime = 0;
    }

    setInterval(function() {
        idleTime += 1000;
        if (idleTime >= idleMax) {
            var currentUrl = window.location.pathname;
            if (currentUrl.indexOf('/auth/') === -1) {
                document.body.insertAdjacentHTML('beforeend',
                    '<div style="position:fixed;top:0;left:0;right:0;bottom:0;' +
                    'background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;">' +
                    '<div style="background:#fff;padding:24px;border-radius:12px;text-align:center;margin:0 20px;max-width:320px;">' +
                    '<p style="margin-bottom:16px;font-size:1rem;">长时间未操作，请刷新页面重新登录。</p>' +
                    '<button onclick="location.reload()" style="padding:12px 32px;' +
                    'background:#4f46e5;color:#fff;border:none;border-radius:8px;font-size:1rem;cursor:pointer;">刷新页面</button>' +
                    '</div></div>');
                idleTime = 0;
            }
        }
    }, 1000);

    document.addEventListener('mousemove', resetIdle);
    document.addEventListener('keypress', resetIdle);
    document.addEventListener('scroll', resetIdle);
    document.addEventListener('touchstart', resetIdle);
    document.addEventListener('click', resetIdle);
})();
