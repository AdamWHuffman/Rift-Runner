import type { LatLngBoundsExpression } from 'leaflet'
import { useLayoutEffect } from 'react'
import { useMap } from 'react-leaflet'

// react-leaflet's declarative `bounds` prop applies fitBounds() in an effect
// that runs *after* the map's first paint at whatever placeholder view it
// started with -- the tile pane's CSS transform gets updated for the new
// view, but tiles already requested/rendered for the placeholder view can be
// left behind at their stale transform offset, producing a torn-looking
// background. Calling fitBounds ourselves in useLayoutEffect -- synchronously,
// before the browser paints anything -- means there's never a placeholder
// view to leave tiles behind from in the first place.
function FitBoundsOnMount({ bounds, padding }: { bounds: LatLngBoundsExpression; padding: [number, number] }) {
  const map = useMap()
  useLayoutEffect(() => {
    map.fitBounds(bounds, { padding, animate: false })
    // A follow-up invalidateSize covers the (rarer) case where the
    // container's own size wasn't final yet at layout-effect time, e.g. a
    // parent still mid CSS-transition.
    const timer = setTimeout(() => map.invalidateSize(), 250)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])
  return null
}

export default FitBoundsOnMount
