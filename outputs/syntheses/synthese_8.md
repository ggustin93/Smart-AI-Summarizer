# [Tutorial] How to Make Webflow Site Load Faster: Episode 1

## Compressing Custom Fonts & Uploading to Webflow

**Author:** Chris T. (chrisfromlumious)  
**Date:** February 22, 2021

### Introduction
Many Webflow users struggle with optimizing their site speed. This tutorial series aims to help you achieve a 100% score on Google Lighthouse and WebAim. In this episode, we focus on optimizing fonts.

### Why Optimize Fonts?
Using Google Fonts directly in Webflow adds the Google API script to your initial page load, which can slow down your site. Instead, using custom fonts can improve performance.

### Steps to Optimize Fonts

1. **Download Google Fonts:**
   - Download the font family you plan to use instead of integrating it via Webflow's Project Settings.

2. **Limit Font Usage:**
   - Use only one font-family and two font weights to minimize file size.

3. **Edit Font Files:**
   - Use FontForge to remove unused glyphs, special characters, and symbols from the font file.

4. **Export Optimized Font:**
   - Export the font in Web Open Font 2.0 (WOFF2) format, which is highly compressed and widely supported by browsers.

### Tools and Resources
- **FontForge:** [Download here](http://bit.ly/3jSeJvi)
- **Understanding and Reducing Font Size:** [Learn more](http://bit.ly/2ZiUH40)

### Related Topics
- [How to upload & manage custom fonts](https://forum.webflow.com/t/how-to-upload-manage-custom-fonts/7480)
- [The ultimate guide to Webflow site performance optimization](https://forum.webflow.com/t/the-ultimate-guide-to-webflow-site-performance-optimization/3018)
- [Loading custom fonts in the Designer UI](https://forum.webflow.com/t/loading-custom-fonts-supporting-that-in-the-designer-ui/1062)
- [Reducing Webflow Javascript files for faster load speed](https://forum.webflow.com/t/reducing-the-webflow-javascript-files-for-faster-load-speed/512)
- [Open sans - Webflow adds unused fonts file requests](https://forum.webflow.com/t/open-sans-webflow-adds-unused-fonts-file-requests/14362)

### Conclusion
By following these steps, you can significantly improve the loading speed of your Webflow site. Stay tuned for more episodes on optimizing your Webflow site performance.

---

**Happy optimizing!**