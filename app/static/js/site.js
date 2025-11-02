const initSlider = () => {
    const slider = document.querySelector('[data-slider]');
    if (!slider) return;

    const slides = slider.querySelectorAll('[data-slide]');
    const controls = slider.querySelectorAll('.slider-btn');
    if (!slides.length) return;

    let activeIndex = Array.from(slides).findIndex((slide) => slide.classList.contains('is-active'));
    if (activeIndex < 0) activeIndex = 0;

    const setActiveSlide = (index) => {
        slides.forEach((slide, idx) => {
            slide.classList.toggle('is-active', idx === index);
            slide.setAttribute('aria-hidden', idx === index ? 'false' : 'true');
        });
        activeIndex = index;
    };

    const goTo = (direction) => {
        const nextIndex = (activeIndex + direction + slides.length) % slides.length;
        setActiveSlide(nextIndex);
    };

    controls.forEach((control) => {
        const action = control.dataset.action;
        if (action === 'prev') {
            control.addEventListener('click', () => goTo(-1));
        }
        if (action === 'next') {
            control.addEventListener('click', () => goTo(1));
        }
    });

    let sliderTimer = window.setInterval(() => goTo(1), 6000);

    slider.addEventListener('mouseenter', () => window.clearInterval(sliderTimer));
    slider.addEventListener('mouseleave', () => {
        sliderTimer = window.setInterval(() => goTo(1), 6000);
    });

    setActiveSlide(activeIndex);
};

const initCartMenu = () => {
    const cartMenu = document.querySelector('.cart-menu');
    if (!cartMenu) return;

    const toggle = cartMenu.querySelector('.cart-toggle');
    const updateExpanded = (expanded) => toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');

    let closeTimer = null;

    const openMenu = () => {
        cartMenu.classList.add('is-open');
        updateExpanded(true);
    };

    const closeMenu = () => {
        cartMenu.classList.remove('is-open');
        updateExpanded(false);
    };

    toggle.addEventListener('click', (event) => {
        event.preventDefault();
        const willOpen = !cartMenu.classList.contains('is-open');
        if (willOpen) {
            openMenu();
        } else {
            closeMenu();
        }
    });

    cartMenu.addEventListener('mouseenter', () => {
        if (closeTimer) {
            window.clearTimeout(closeTimer);
            closeTimer = null;
        }
        openMenu();
    });

    cartMenu.addEventListener('mouseleave', () => {
        closeTimer = window.setTimeout(() => {
            closeMenu();
            closeTimer = null;
        }, 150);
    });

    cartMenu.addEventListener('focusin', openMenu);
    cartMenu.addEventListener('focusout', (event) => {
        if (!cartMenu.contains(event.relatedTarget)) {
            closeMenu();
        }
    });

    document.addEventListener('click', (event) => {
        if (!cartMenu.contains(event.target) && cartMenu.classList.contains('is-open')) {
            closeMenu();
        }
    });
};

window.addEventListener('DOMContentLoaded', () => {
    initSlider();
    initCartMenu();
});
