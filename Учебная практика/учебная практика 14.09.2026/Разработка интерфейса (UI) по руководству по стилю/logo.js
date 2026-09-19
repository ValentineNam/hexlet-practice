export function createLogo(partner) {
  const shape = partner.logo.shape;
  const letter = partner.logo.letter;
  const element = document.createElement('div');
  element.className = `partner-logo partner-logo--${shape}`;
  element.style.background = partner.logo.bg;
  element.style.color = partner.logo.color;

  const letterNode = document.createElement('span');
  letterNode.className = 'logo-letter';
  letterNode.textContent = letter;
  element.appendChild(letterNode);

  return element;
}
