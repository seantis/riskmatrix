$(function() {
    // disable these buttons on submit to prevent multiple submits
    $('.btn-submit').click(function(event) {
        $(this).addClass('disabled');
        $(this).attr('aria-disabled', 'true');
        var btn = new bootstrap.Button(this);
        btn.toggle();
    });
    // initialize tooltips
    new bootstrap.Tooltip(document.body, {selector: '[data-bs-toggle="tooltip"]'});
});


/*!
 * Color mode toggler for Bootstrap's docs (https://getbootstrap.com/)
 * Copyright 2011-2024 The Bootstrap Authors
 * Licensed under the Creative Commons Attribution 3.0 Unported License.
 */

(() => {
    'use strict'
  
    const getStoredTheme = () => localStorage.getItem('theme')
    const setStoredTheme = theme => localStorage.setItem('theme', theme)
  
    const getPreferredTheme = () => {
      const storedTheme = getStoredTheme()
      if (storedTheme) {
        return storedTheme
      }
  
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }

    const showActiveTheme = (theme, focus = false) => {
      const themeSwitcher = document.querySelector('#bd-theme')
  
      if (!themeSwitcher) {
        return
      }
  
      const themeSwitcherText = document.querySelector('#bd-theme-text')
      const activeThemeIcon = document.querySelector('.theme-icon-active')
      const btnToActive = document.querySelector(`[data-bs-theme-value="${theme}"]`)
      
      // Remove all existing icon classes except 'theme-icon-active'
      activeThemeIcon.className = 'fa theme-icon-active'
      
      // Add the appropriate icon class based on the theme
      if (theme === 'dark' || (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        activeThemeIcon.classList.add('fa-moon')
      } else if (theme === 'light' || (theme === 'auto' && !window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        activeThemeIcon.classList.add('fa-sun')
      } else if (theme === 'auto') {
        activeThemeIcon.classList.add('fa-laptop')
      }
  
      document.querySelectorAll('[data-bs-theme-value]').forEach(element => {
        element.classList.remove('active')
        element.setAttribute('aria-pressed', 'false')
      })
  
      btnToActive.classList.add('active')
      btnToActive.setAttribute('aria-pressed', 'true')
      const themeSwitcherLabel = `${themeSwitcherText.textContent} (${btnToActive.dataset.bsThemeValue})`
      themeSwitcher.setAttribute('aria-label', themeSwitcherLabel)
  
      if (focus) {
        themeSwitcher.focus()
      }
    }
  
    const setTheme = theme => {
      const resolvedTheme = theme === 'auto' ? 
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : theme;
      
      document.documentElement.setAttribute('data-bs-theme', resolvedTheme)
      
      // Create and dispatch the theme change event
      const event = new CustomEvent('bs-theme-changed', { 
        detail: { theme: resolvedTheme }
      });
      document.documentElement.dispatchEvent(event);
      
      // Update the theme icon
      showActiveTheme(theme);
    }
  
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      const storedTheme = getStoredTheme()
      if (storedTheme !== 'light' && storedTheme !== 'dark') {
        setTheme(getPreferredTheme())
      }
    })
  
    window.addEventListener('DOMContentLoaded', () => {
      showActiveTheme(getPreferredTheme())
  
      document.querySelectorAll('[data-bs-theme-value]')
        .forEach(toggle => {
          toggle.addEventListener('click', () => {
            const theme = toggle.getAttribute('data-bs-theme-value')
            setStoredTheme(theme)
            setTheme(theme)
          })
        })
    })

    // Initialize theme
    setTheme(getPreferredTheme())
  })()