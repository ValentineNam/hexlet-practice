export function createLogo(partner) {
  const logo = document.createElement('span');
  logo.className = `partner-logo partner-logo--${partner.logo.shape}`;
  logo.style.setProperty('--logo-background', partner.logo.bg);
  logo.style.setProperty('--logo-color', partner.logo.color);
  logo.setAttribute('aria-hidden', 'true');

  const letter = document.createElement('span');
  letter.className = 'logo-letter';
  letter.textContent = partner.logo.letter;
  logo.append(letter);

  return logo;
}
