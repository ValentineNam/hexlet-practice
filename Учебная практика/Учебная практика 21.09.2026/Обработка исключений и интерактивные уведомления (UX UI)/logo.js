export function createLogo(partner) {
  const logo = document.createElement('span');
  const shape = partner.logo?.shape || 'circle';
  logo.className = `partner-logo partner-logo--${shape}`;
  logo.style.setProperty('--logo-background', partner.logo?.bg || '#315c51');
  logo.style.setProperty('--logo-color', partner.logo?.color || '#fffaf0');
  logo.setAttribute('aria-hidden', 'true');

  const letter = document.createElement('span');
  letter.className = 'logo-letter';
  letter.textContent = partner.logo?.letter || partner.company_name?.[0] || 'П';
  logo.append(letter);
  return logo;
}
