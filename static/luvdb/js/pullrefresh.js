// Check if running in standalone mode
if (window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches) {
    let startY = 0;
    let distance = 0;
    const threshold = 100; // Minimum distance to trigger refresh
    const refreshBox = document.getElementById('refresh-box');
    
    document.addEventListener('touchstart', function(e) {
      if (window.scrollY === 0) {
        startY = e.touches[0].pageY;
      }
    }, false);
    
    document.addEventListener('touchmove', function(e) {
      if (startY !== 0) {
        distance = e.touches[0].pageY - startY;
        if (distance > 0) {
          refreshBox.style.height = `${distance}px`;
          refreshBox.classList.remove('hidden');
        }
      }
    }, false);
    
    document.addEventListener('touchend', function(e) {
      startY = 0;
      refreshBox.style.height = '0px';
      refreshBox.classList.add('hidden');
      if (distance >= threshold) {
        // Trigger refresh action here
        location.reload();
      }
      distance = 0;
    }, false);
    
}
